#!/usr/bin/env python3
"""
Tier 2 test suite for game_engine.py (GameEngine).

Run with: python test_game_engine.py
"""

import os
import sys
import time
import traceback

from game_engine import GameEngine
from openingbook import OpeningBook

results = []

# Shared across tests — loading the ~3,800-line ECO dataset is read-only and
# stateless, so every GameEngine instance below can safely reuse it.
BOOK = OpeningBook()


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


def _engine(skill_level=5, depth=8):
    return GameEngine(skill_level=skill_level, depth=depth, opening_book=BOOK)


def test_init():
    g = _engine()
    assert g.board.fen().split(" ")[0] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    assert g.get_moves() == []
    assert g.is_game_over() is False
    assert g.get_result() is None


def test_legal_move():
    g = _engine()
    ok, msg = g.move("e2e4")
    assert ok, msg
    assert "e4" in msg
    moves = g.get_moves()
    assert len(moves) == 1
    assert moves[0]["san"] == "e4"
    assert moves[0]["uci"] == "e2e4"


def test_move_record_has_alternatives_and_opening():
    g = _engine()
    g.move("e2e4")
    record = g.get_moves()[0]
    assert isinstance(record["alternatives"], list)
    assert record["eco"] is not None
    assert record["opening_name"] is not None
    for alt in record["alternatives"]:
        assert "san" in alt and "eval" in alt
        assert alt["san"] != record["san"]  # played move must not appear as its own alternative


def test_illegal_move_rejected():
    g = _engine()
    ok, msg = g.move("e2e5")  # not a legal pawn move
    assert not ok
    assert len(g.get_moves()) == 0


def test_malformed_move_rejected():
    g = _engine()
    ok, msg = g.move("zz99")
    assert not ok


def test_classification_attached():
    g = _engine()
    g.move("e2e4")
    moves = g.get_moves()
    assert moves[0]["classification"] is not None
    assert moves[0]["classification"] == "Book"  # 1. e4 is textbook opening theory


def test_get_best_move_does_not_apply_it():
    g = _engine()
    uci, eval_info = g.get_best_move()
    assert uci is not None
    assert "eval" in eval_info and "mate" in eval_info
    assert g.get_moves() == []  # get_best_move must not mutate game state


def test_set_depth_changes_search_depth_and_stats():
    g = _engine(depth=6)
    g.get_best_move()
    assert g.move_stats[0]["depth"] == 6

    g.set_depth(4)
    g.get_best_move()
    assert g.move_stats[1]["depth"] == 4
    assert g._engine.depth == 4


def test_get_engine_stats_empty_and_populated():
    g = _engine(depth=6)
    empty = g.get_engine_stats()
    assert empty["total_moves"] == 0
    assert empty["avg_time_ms"] is None

    g.get_best_move()
    g.get_best_move()
    stats = g.get_engine_stats()
    assert stats["total_moves"] == 2
    assert stats["avg_depth"] == 6
    assert stats["avg_time_ms"] > 0
    assert stats["min_time_ms"] <= stats["max_time_ms"]


def test_top_moves_cache_reused_across_get_best_move_and_move():
    g = _engine()
    uci, _ = g.get_best_move()
    # If move() re-queried Stockfish from scratch this would still work, but
    # it should be near-instant since it reuses the cached top-moves lookup.
    start = time.time()
    ok, _ = g.move(uci)
    elapsed = time.time() - start
    assert ok
    assert elapsed < 0.05, f"expected a cache hit (<50ms), took {elapsed*1000:.1f}ms"


def test_get_state_shape():
    g = _engine()
    g.move("e2e4")
    state = g.get_state()
    for key in ("game_id", "fen", "board", "moves", "turn", "status", "result", "last_move", "legal_moves", "evaluation"):
        assert key in state, f"missing key: {key}"
    assert state["turn"] == "black"
    assert state["status"] == "playing"
    assert state["last_move"] == "e2e4"
    assert len(state["board"]) == 8 and len(state["board"][0]) == 8
    assert state["board"][0] == ["r", "n", "b", "q", "k", "b", "n", "r"]  # rank 8, black back row
    assert state["board"][7] == ["R", "N", "B", "Q", "K", "B", "N", "R"]  # rank 1, white back row
    assert state["evaluation"]["eval"] is not None


def test_checkmate_status_and_result():
    g = _engine()
    for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:  # Fool's Mate
        ok, msg = g.move(uci)
        assert ok, msg
    assert g.is_game_over() is True
    assert g.get_status() == "checkmate"
    assert g.get_result() == "black_win"
    state = g.get_state()
    assert state["legal_moves"] == []


def test_stalemate_status():
    g = _engine()
    g.board.set_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert g.get_status() == "stalemate"
    assert g.get_result() == "draw"


def test_undo():
    g = _engine()
    g.move("e2e4")
    g.move("e7e5")
    ok, msg = g.undo()
    assert ok, msg
    assert len(g.get_moves()) == 1
    assert g.get_moves()[0]["uci"] == "e2e4"


def test_save_and_export_no_moves_returns_none():
    g = _engine()
    game_id, path = g.save_and_export()
    assert game_id is None and path is None


def test_save_and_export_writes_db_and_pgn(tmp_dir):
    import chess.pgn
    from database import GameDatabase

    g = _engine()
    for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        g.move(uci)

    game_id, path = g.save_and_export(games_dir=tmp_dir)
    assert game_id is not None
    assert os.path.exists(path)

    with open(path, encoding="utf-8") as fh:
        parsed = chess.pgn.read_game(fh)
    assert parsed.headers["Result"] == "0-1"
    assert "Fool's Mate" in parsed.headers.get("Opening", "")

    db = GameDatabase()
    try:
        row = db.get_game(game_id)
        assert row["result"] == "0-1"
        moves = db.get_moves(game_id)
        assert len(moves) == 4
        assert moves[0]["classification"] == "Book"
    finally:
        db.close()


def test_black_to_move_perspective_no_crash():
    # Regression guard: classification math must not blow up when Black moves.
    g = _engine()
    g.move("e2e4")
    ok, msg = g.move("e7e5")
    assert ok, msg
    assert g.get_moves()[1]["classification"] is not None


def main():
    print("=" * 60)
    print("  JARVIS Chess - Tier 2 GameEngine Test Suite")
    print("=" * 60)

    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="jarvis_chess_ge_test_")

    tests = [
        ("Init: fresh board, empty history", test_init),
        ("Legal move applies and records SAN", test_legal_move),
        ("Move record includes alternatives + opening tag", test_move_record_has_alternatives_and_opening),
        ("Illegal move rejected, no record added", test_illegal_move_rejected),
        ("Malformed move string rejected", test_malformed_move_rejected),
        ("Classification attached to move record", test_classification_attached),
        ("get_best_move does not mutate state", test_get_best_move_does_not_apply_it),
        ("set_depth changes search depth + recorded stats", test_set_depth_changes_search_depth_and_stats),
        ("get_engine_stats: empty and populated", test_get_engine_stats_empty_and_populated),
        ("Top-moves cache reused across get_best_move->move", test_top_moves_cache_reused_across_get_best_move_and_move),
        ("get_state() shape and board grid orientation", test_get_state_shape),
        ("Checkmate: status + result (Fool's Mate)", test_checkmate_status_and_result),
        ("Stalemate: status + result", test_stalemate_status),
        ("Undo reverts last move", test_undo),
        ("save_and_export with no moves -> (None, None)", test_save_and_export_no_moves_returns_none),
        ("save_and_export writes DB row + PGN", lambda: test_save_and_export_writes_db_and_pgn(tmp_dir)),
        ("Black-to-move classification doesn't crash", test_black_to_move_perspective_no_crash),
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

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
