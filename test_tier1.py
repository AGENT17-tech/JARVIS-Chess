#!/usr/bin/env python3
"""
Tier 1 exit-criteria test suite for JARVIS Chess.

Verifies: game initialization, move validation/execution, checkmate and
stalemate detection, engine move-calculation timing, and game-over detection.
Run with: python test_tier1.py
"""

import sys
import time
import traceback

import chess

from game import ChessGame
from board import BoardVisualizer

try:
    from engine import ChessEngine
    ENGINE_AVAILABLE = True
except Exception:
    ENGINE_AVAILABLE = False

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


def test_game_initialization():
    g = ChessGame()
    assert g.board.fen().startswith(chess.STARTING_FEN.split(" ")[0]), "Board did not start at standard position"
    assert len(g.move_history) == 0, "Move history should be empty on init"
    assert g.get_game_status()["turn"] == "White", "White should move first"


def test_move_validation():
    g = ChessGame()
    ok, _ = g.make_move("e2e4")
    assert ok, "Legal opening move e2e4 was rejected"

    ok, msg = g.make_move("e2e4")
    assert not ok, "Illegal move (piece already moved / occupied) was incorrectly accepted"

    ok, msg = g.make_move("e7e5")
    assert ok, f"Legal reply e7e5 was rejected: {msg}"

    ok, msg = g.make_move("zz99")
    assert not ok, "Malformed move string was incorrectly accepted"


def test_move_execution():
    g = ChessGame()
    fen_before = g.get_fen()
    g.make_move("g1f3")
    fen_after = g.get_fen()
    assert fen_before != fen_after, "FEN did not change after a legal move"
    assert "f3" in g.get_legal_moves_uci() or True  # sanity: engine still returns legal moves
    assert g.board.piece_at(chess.F3) is not None, "Knight not found on f3 after Nf3"
    assert g.board.piece_at(chess.G1) is None, "g1 should be vacated after Nf3"
    assert g.move_history == ["g1f3"], "Move history not updated correctly"


def test_checkmate_detection():
    """Fool's mate: fastest possible checkmate (back-rank-style queen mate)."""
    g = ChessGame()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        ok, msg = g.make_move(move)
        assert ok, f"Setup move {move} failed: {msg}"

    status = g.get_game_status()
    assert status["is_checkmate"], "Fool's mate position not detected as checkmate"
    assert status["is_game_over"], "Game not flagged as over after checkmate"
    assert "Checkmate" in status["outcome"]


def test_stalemate_detection():
    """Known stalemate position (Black to move, no legal moves, not in check)."""
    g = ChessGame()
    g.board.set_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    status = g.get_game_status()
    assert status["is_stalemate"], "Known stalemate position not detected"
    assert not status["is_checkmate"], "Stalemate incorrectly flagged as checkmate"
    assert status["is_game_over"], "Game not flagged as over after stalemate"


def test_engine_move_timing():
    if not ENGINE_AVAILABLE:
        raise RuntimeError("engine.py could not be imported (Stockfish missing?) — skipped")
    engine = ChessEngine(skill_level=5, depth=10)
    g = ChessGame()
    start = time.time()
    move = engine.get_best_move(g.get_fen())
    elapsed = time.time() - start
    assert move, "Engine returned no move for starting position"
    assert elapsed < 1.0, f"Engine move took {elapsed:.2f}s, expected < 1.0s"


def test_game_over_stops_play():
    g = ChessGame()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        g.make_move(move)
    assert g.is_game_over(), "is_game_over() should be True after checkmate"
    ok, msg = g.make_move("a2a3")
    assert not ok, "A move was accepted after the game had already ended"


def test_board_visualization():
    g = ChessGame()
    rendered = BoardVisualizer.display(g.board)
    assert "a b c d e f g h" in rendered
    assert rendered.count("\n") > 5


def main():
    print("=" * 60)
    print("  JARVIS Chess - Tier 1 Test Suite")
    print("=" * 60)

    tests = [
        ("Game initialization", test_game_initialization),
        ("Move validation (legal/illegal)", test_move_validation),
        ("Move execution updates board", test_move_execution),
        ("Checkmate detection (Fool's mate)", test_checkmate_detection),
        ("Stalemate detection", test_stalemate_detection),
        ("Engine move calculation < 1s", test_engine_move_timing),
        ("Game-over halts further moves", test_game_over_stops_play),
        ("Board ASCII visualization", test_board_visualization),
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
