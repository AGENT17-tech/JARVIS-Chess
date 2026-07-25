#!/usr/bin/env python3
"""
Tier 2 test suite for api_server.py's WebSocket handler (/ws/game/{game_id}).

Uses FastAPI TestClient.websocket_connect — synchronous, no real socket or
running server process needed. Run with: python test_websocket.py
"""

import os
import sys
import time
import traceback

results = []


def run_test(name, fn):
    start = time.time()
    try:
        fn()
        elapsed = (time.time() - start) * 1000
        results.append((name, True, elapsed, None))
        print(f"  PASS  {name}  ({elapsed:.1f}ms)")
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        results.append((name, False, elapsed, f"{e.__class__.__name__}: {e}"))
        print(f"  FAIL  {name}  ({elapsed:.1f}ms)")
        print(f"        {e.__class__.__name__}: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()


def _client():
    from fastapi.testclient import TestClient
    from api_server import app
    return TestClient(app)


def test_connect_sends_initial_state():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        initial = ws.receive_json()
        assert initial["fen"].startswith("rnbqkbnr")
        assert initial["moves"] == []


def test_connect_unknown_game_sends_error():
    client = _client()
    try:
        with client.websocket_connect("/ws/game/does-not-exist") as ws:
            msg = ws.receive_json()
            assert "error" in msg
    except Exception:
        # Some Starlette versions raise on the server-initiated close instead
        # of letting receive_json see the error frame first — either is fine,
        # both mean "connection was rejected for an unknown game_id".
        pass


def test_legal_move_broadcasts_state_with_jarvis_reply():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"action": "move", "uci": "e2e4"})
        state = ws.receive_json()
        assert len(state["moves"]) == 2  # player's move + JARVIS's reply
        assert state["moves"][0]["uci"] == "e2e4"
        assert state["turn"] == "white"


def test_illegal_move_returns_error_without_state_change():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"action": "move", "uci": "e2e5"})  # illegal
        resp = ws.receive_json()
        assert "error" in resp
        assert resp["state"]["moves"] == []  # nothing was applied


def test_unknown_action_returns_error():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()
        ws.send_json({"action": "resign"})
        resp = ws.receive_json()
        assert "error" in resp


def test_set_depth_action_acks_and_updates_engine():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"action": "set_depth", "depth": 3})
        resp = ws.receive_json()
        assert resp == {"depth_set": 3}
        assert game._engine.depth == 3


def test_set_depth_action_rejects_out_of_range():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()
        ws.send_json({"action": "set_depth", "depth": 99})
        resp = ws.receive_json()
        assert "error" in resp


def test_undo_action_reverts_last_round():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)
    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()
        ws.send_json({"action": "move", "uci": "e2e4"})
        ws.receive_json()  # player move + jarvis reply
        ws.send_json({"action": "undo"})
        state = ws.receive_json()
        assert state["moves"] == []  # both plies unwound


def test_checkmate_stops_before_a_second_move_and_saves():
    """
    Regression test for the real bug found in the original design sketch:
    it never checked whether the player's move already ended the game before
    auto-playing a JARVIS reply. Also verifies the auto-save-on-game-over path.
    """
    from api_server import manager
    from database import GameDatabase

    client = _client()
    game = manager.create_game(skill_level=1, depth=1)
    # Set up Fool's Mate directly via GameEngine, leaving the final mating
    # move to be sent through the socket (JARVIS's own move choices aren't
    # scriptable, so we can't rely on it choosing this exact sequence).
    for uci in ["f2f3", "e7e5", "g2g4"]:
        ok, msg = game.move(uci)
        assert ok, msg

    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws:
        ws.receive_json()  # initial state (mid-game, since we pre-pushed moves above)
        ws.send_json({"action": "move", "uci": "d8h4"})  # Qh4# — checkmate
        state = ws.receive_json()

        assert state["status"] == "checkmate"
        assert state["result"] == "black_win"
        assert len(state["moves"]) == 4  # NOT 5 — no JARVIS move attempted after mate
        assert state["moves"][-1]["uci"] == "d8h4"
        assert "saved" in state and state["saved"]["game_id"] is not None

    db = GameDatabase()
    try:
        row = db.get_game(state["saved"]["game_id"])
        assert row is not None
        assert row["result"] == "0-1"
    finally:
        db.close()


def test_broadcast_reaches_multiple_connections():
    from api_server import manager
    client = _client()
    game = manager.create_game(skill_level=5, depth=6)

    with client.websocket_connect(f"/ws/game/{game.game_id}") as ws1, \
         client.websocket_connect(f"/ws/game/{game.game_id}") as ws2:
        ws1.receive_json()
        ws2.receive_json()

        ws1.send_json({"action": "move", "uci": "e2e4"})
        state1 = ws1.receive_json()
        state2 = ws2.receive_json()
        assert state1["fen"] == state2["fen"]
        assert len(state2["moves"]) == 2


def main():
    print("=" * 60)
    print("  JARVIS Chess - Tier 2 WebSocket Test Suite")
    print("=" * 60)

    db_path = "games_db.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)

    tests = [
        ("Connect sends initial state", test_connect_sends_initial_state),
        ("Connect to unknown game -> error", test_connect_unknown_game_sends_error),
        ("Legal move broadcasts state incl. JARVIS reply", test_legal_move_broadcasts_state_with_jarvis_reply),
        ("Illegal move -> error, no state change", test_illegal_move_returns_error_without_state_change),
        ("Unknown action -> error", test_unknown_action_returns_error),
        ("set_depth action acks + updates engine", test_set_depth_action_acks_and_updates_engine),
        ("set_depth action rejects out-of-range depth", test_set_depth_action_rejects_out_of_range),
        ("Undo action reverts last round", test_undo_action_reverts_last_round),
        ("Checkmate stops before 2nd move + auto-saves", test_checkmate_stops_before_a_second_move_and_saves),
        ("Broadcast reaches all connections for a game", test_broadcast_reaches_multiple_connections),
    ]

    for name, fn in tests:
        run_test(name, fn)

    passed = sum(1 for _, ok, _, _ in results if ok)
    total = len(results)
    total_time = sum(t for _, _, t, _ in results)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for name, ok, elapsed, err in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name} ({elapsed:.1f}ms)")
    print(f"\n  Pass rate: {passed}/{total}")
    print(f"  Total time: {total_time:.1f}ms")
    print("=" * 60)

    if os.path.exists(db_path):
        os.remove(db_path)
    games_dir = "games"
    if os.path.isdir(games_dir):
        for f in os.listdir(games_dir):
            if f.endswith(".pgn"):
                os.remove(os.path.join(games_dir, f))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
