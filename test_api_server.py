#!/usr/bin/env python3
"""
Tier 2 test suite for api_server.py (FastAPI REST routes).

Uses FastAPI's TestClient — no real server process or socket needed. Run
with: python test_api_server.py

Uses the default games_db.sqlite (same as a real run of the server) since
api_server.py's routes always construct GameDatabase() with its default
path; the file is wiped at the start/end of this run for a clean slate.
"""

import io
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


def _new_game(client, skill_level=5, depth=6):
    r = client.post("/api/games/new", params={"skill_level": skill_level, "depth": depth})
    assert r.status_code == 200, r.text
    return r.json()["game_id"], r.json()["state"]


def test_root():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, state = _new_game(client)
    assert game_id.startswith("game_")
    assert state["fen"].startswith("rnbqkbnr")
    assert state["moves"] == []


def test_get_state():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    r = client.get(f"/api/games/{game_id}/state")
    assert r.status_code == 200
    assert r.json()["game_id"] == game_id


def test_get_state_404():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/games/nope/state")
    assert r.status_code == 404


def test_move_applies_and_auto_replies():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)

    r = client.post(f"/api/games/{game_id}/move", json={"uci": "e2e4"})
    assert r.status_code == 200
    state = r.json()
    assert len(state["moves"]) == 2  # player's move + JARVIS's auto-reply
    assert state["moves"][0]["uci"] == "e2e4"
    assert state["turn"] == "white"


def test_illegal_move_returns_400():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    r = client.post(f"/api/games/{game_id}/move", json={"uci": "e2e5"})
    assert r.status_code == 400


def test_move_on_missing_game_404():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/api/games/nope/move", json={"uci": "e2e4"})
    assert r.status_code == 404


def test_get_moves_route():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    client.post(f"/api/games/{game_id}/move", json={"uci": "e2e4"})
    r = client.get(f"/api/games/{game_id}/moves")
    assert r.status_code == 200
    assert len(r.json()["moves"]) == 2


def test_list_games_includes_created_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    r = client.get("/api/games")
    ids = [g["game_id"] for g in r.json()["games"]]
    assert game_id in ids


def test_end_game_saves_and_removes_from_manager():
    from api_server import app, manager
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    client.post(f"/api/games/{game_id}/move", json={"uci": "e2e4"})

    r = client.post(f"/api/games/{game_id}/end")
    assert r.status_code == 200
    assert r.json()["saved_game_id"] is not None
    assert manager.get_game(game_id) is None  # removed from the in-memory manager

    r2 = client.get(f"/api/games/{game_id}/state")
    assert r2.status_code == 404  # gone after /end


def test_engine_stats_route():
    from api_server import app, manager
    from fastapi.testclient import TestClient
    client = TestClient(app)

    game = manager.create_game(skill_level=5, depth=6)
    game.move("e2e4")
    game.get_best_move()  # records one JARVIS-style timing sample

    r = client.get(f"/api/games/{game.game_id}/engine-stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total_moves"] == 1
    assert stats["avg_time_ms"] > 0
    assert stats["avg_depth"] == 6


def test_engine_stats_route_missing_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/games/nope/engine-stats")
    assert r.status_code == 404


def test_games_history_lists_saved_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    client.post(f"/api/games/{game_id}/move", json={"uci": "e2e4"})
    saved = client.post(f"/api/games/{game_id}/end").json()

    r = client.get("/api/games/history")
    assert r.status_code == 200
    ids = [g["id"] for g in r.json()["games"]]
    assert saved["saved_game_id"] in ids


def test_games_history_replay_analyzed_local_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    game_id, _ = _new_game(client)
    client.post(f"/api/games/{game_id}/move", json={"uci": "e2e4"})
    saved = client.post(f"/api/games/{game_id}/end").json()

    r = client.get(f"/api/games/history/{saved['saved_game_id']}/replay")
    assert r.status_code == 200
    data = r.json()
    assert data["analyzed"] is True
    assert len(data["moves"]) == 2  # player's move + JARVIS's auto-reply
    assert data["moves"][0]["uci"] == "e2e4"
    assert data["moves"][0]["fen"] is not None


def test_games_history_replay_unanalyzed_import_reconstructs_fen():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    client.post(
        "/api/import/pgn",
        files={"file": ("sample.pgn", io.BytesIO(SAMPLE_PGN), "application/x-chess-pgn")},
    )
    history = client.get("/api/games/history?source=manual_import").json()["games"]
    game_id = history[-1]["id"]

    r = client.get(f"/api/games/history/{game_id}/replay")
    assert r.status_code == 200
    data = r.json()
    assert data["analyzed"] is False
    assert len(data["moves"]) == 5  # 1.e4 e5 2.Nf3 Nc6 3.Bb5
    assert data["moves"][0]["san"] == "e4"
    assert data["moves"][0]["eval"] is None
    assert data["moves"][-1]["san"] == "Bb5"


def test_games_history_replay_missing_game():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/games/history/999999/replay")
    assert r.status_code == 404


def test_openings_stats_route():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/openings/stats")
    assert r.status_code == 200
    assert "analytics" in r.json() and "openings" in r.json()


def test_openings_stats_includes_mistake_count():
    from api_server import app, manager
    from database import GameDatabase
    from fastapi.testclient import TestClient
    client = TestClient(app)

    game = manager.create_game(skill_level=5, depth=6)
    for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        ok, msg = game.move(uci)
        assert ok, msg
    game_id, _ = game.save_and_export()

    db = GameDatabase()
    try:
        db.save_mistake({"game_id": game_id, "eco": "A00", "severity": "Minor", "played_move": "x", "book_move": "y"})
    finally:
        db.close()

    r = client.get("/api/openings/stats")
    assert r.status_code == 200
    row = next(o for o in r.json()["openings"] if o["eco"] == "A00")
    assert row["mistake_count"] == 1


def test_openings_analysis_route_unknown_eco():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/openings/Z99/analysis")
    assert r.status_code == 200
    assert r.json()["eco"] == "Z99"
    assert r.json()["total_games"] == 0


def test_favorite_route():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/api/openings/Test Opening XYZ/favorite", json={"status": "study"})
    assert r.status_code == 200
    assert r.json()["favorite_status"] == "study"


def test_favorite_route_bad_status():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/api/openings/Test Opening XYZ/favorite", json={"status": "bogus"})
    assert r.status_code == 400


SAMPLE_PGN = b"""[Event "Live Chess"]
[White "testwhite"]
[Black "testblack"]
[Result "1-0"]
[ECO "C60"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0
"""


def test_import_pgn_route():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post(
        "/api/import/pgn",
        files={"file": ("sample.pgn", io.BytesIO(SAMPLE_PGN), "application/x-chess-pgn")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1
    assert r.json()["errors"] == 0


def test_import_chesscom_live():
    if os.environ.get("RUN_LIVE_NETWORK_TESTS") != "1":
        return  # opt-in only — real chess.com API call, same convention as test_tier1_5.py
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/api/import/chesscom/hikaru", params={"months": 1})
    assert r.status_code == 200
    assert r.json()["imported"] > 0


def test_puzzle_random_live():
    if os.environ.get("RUN_LIVE_NETWORK_TESTS") != "1":
        return  # opt-in only — real lichess.org API call, same convention as test_import_chesscom_live
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/api/puzzle/random")
    assert r.status_code == 200
    data = r.json()
    assert data["fen"]
    assert data["solution_move"]
    assert data["rating"] > 0


def test_puzzle_from_lichess_reshapes_response():
    # Uses a fixed real lichess API response (captured via curl) instead of a
    # live call, so this test's normal (non-opt-in) run still exercises the
    # reshaping logic — board replay, solution_move selection — without a
    # network dependency.
    from api_server import _puzzle_from_lichess
    sample = {
        "game": {
            "pgn": "e4 d5 exd5 Nf6 Nc3 e6 dxe6 Bxe6 Nf3 Bb4 Bd3 Nc6 a3 Bxc3 dxc3 "
                   "Bg4 O-O O-O h3 Bh5 Be3 Ne5 Qe2 Nxf3+ gxf3 Re8 Rad1 Nd5 c4 Nxe3",
        },
        "puzzle": {
            "id": "esXlm",
            "rating": 1509,
            "solution": ["d3h7", "g8h7", "d1d8", "a8d8", "f2e3"],
            "themes": ["middlegame", "advantage", "long", "discoveredAttack"],
            "initialPly": 29,
        },
    }
    puzzle = _puzzle_from_lichess(sample)
    assert puzzle["id"] == "esXlm"
    assert puzzle["solution_move"] == "g8h7"
    assert puzzle["rating"] == 1509
    assert puzzle["themes"] == ["middlegame", "advantage", "long", "discoveredAttack"]
    # returned fen is the position AFTER solution[0] ("d3h7", Bxh7+) is
    # applied — black king is still on g8, in check, waiting for the
    # player to find solution[1] ("g8h7", Kxh7)
    import chess
    board = chess.Board(puzzle["fen"])
    assert board.piece_at(chess.G8) is not None
    assert board.is_check()


def test_puzzle_solved_and_stats():
    from api_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    r = client.post("/api/puzzle/solved", json={"puzzle_id": "abc123", "correct": True})
    assert r.status_code == 200
    client.post("/api/puzzle/solved", json={"puzzle_id": "def456", "correct": False})

    r = client.get("/api/puzzle/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total"] == 2
    assert stats["correct"] == 1
    assert stats["accuracy"] == 0.5


def main():
    print("=" * 60)
    print("  JARVIS Chess - Tier 2 API Server Test Suite")
    print("=" * 60)

    db_path = "games_db.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)

    tests = [
        ("GET / root health check", test_root),
        ("POST /api/games/new", test_create_game),
        ("GET /api/games/{id}/state", test_get_state),
        ("GET /api/games/{id}/state 404 on missing", test_get_state_404),
        ("POST /api/games/{id}/move applies + auto-replies", test_move_applies_and_auto_replies),
        ("POST /api/games/{id}/move illegal -> 400", test_illegal_move_returns_400),
        ("POST /api/games/{id}/move missing game -> 404", test_move_on_missing_game_404),
        ("GET /api/games/{id}/moves", test_get_moves_route),
        ("GET /api/games lists created game", test_list_games_includes_created_game),
        ("POST /api/games/{id}/end saves + removes", test_end_game_saves_and_removes_from_manager),
        ("GET /api/games/{id}/engine-stats", test_engine_stats_route),
        ("GET /api/games/{id}/engine-stats missing game -> 404", test_engine_stats_route_missing_game),
        ("GET /api/games/history lists saved game", test_games_history_lists_saved_game),
        ("GET /api/games/history/{id}/replay (analyzed local game)", test_games_history_replay_analyzed_local_game),
        ("GET /api/games/history/{id}/replay (unanalyzed import)", test_games_history_replay_unanalyzed_import_reconstructs_fen),
        ("GET /api/games/history/{id}/replay missing game -> 404", test_games_history_replay_missing_game),
        ("GET /api/openings/stats", test_openings_stats_route),
        ("GET /api/openings/stats includes mistake_count", test_openings_stats_includes_mistake_count),
        ("GET /api/openings/{eco}/analysis (unknown eco)", test_openings_analysis_route_unknown_eco),
        ("POST /api/openings/{name}/favorite", test_favorite_route),
        ("POST /api/openings/{name}/favorite bad status -> 400", test_favorite_route_bad_status),
        ("POST /api/import/pgn (fixture)", test_import_pgn_route),
        ("POST /api/import/chesscom/{user} (opt-in live)", test_import_chesscom_live),
        ("GET /api/puzzle/random (opt-in live)", test_puzzle_random_live),
        ("_puzzle_from_lichess reshapes response", test_puzzle_from_lichess_reshapes_response),
        ("POST /api/puzzle/solved + GET /api/puzzle/stats", test_puzzle_solved_and_stats),
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

    for path in (db_path,):
        if os.path.exists(path):
            os.remove(path)
    games_dir = "games"
    if os.path.isdir(games_dir):
        for f in os.listdir(games_dir):
            if f.endswith(".pgn"):
                os.remove(os.path.join(games_dir, f))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
