#!/usr/bin/env python3
"""
Tier 1.5 test suite for JARVIS Chess (PGN export, chess.com import, move
classification, opening detection/tracking, database, favorites).

Run with: python test_tier1_5.py
Live network tests (against the real chess.com API) are skipped by default;
set RUN_LIVE_NETWORK_TESTS=1 to include them.
"""

import io
import os
import sys
import time
import traceback

import chess
import chess.pgn

from database import GameDatabase
from openingbook import OpeningBook
from pgnhandler import PgnExporter
from moveanalyzer import (
    MoveAnalyzer,
    LABEL_BOOK,
    LABEL_BRILLIANT,
    LABEL_EXCELLENT,
    LABEL_GOOD,
    LABEL_INACCURACY,
    LABEL_MISTAKE,
    LABEL_BLUNDER,
    LABEL_MISSED_WIN,
)
from chesscom_integration import ChessComImporter
from openingtracker import OpeningMistakeTracker, SEVERITY_MINOR, SEVERITY_CRITICAL

results = []

# Loaded once — the TSV parse takes a noticeable fraction of a second and is
# read-only/stateless, so every test can safely share it.
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


# ---------------------------------------------------------------------------
# database.py
# ---------------------------------------------------------------------------

def test_db_schema_creates_tables():
    db = GameDatabase(":memory:")
    tables = {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for expected in ("games", "moves", "openings", "mistakes"):
        assert expected in tables, f"Missing table: {expected}"
    db.close()


def test_db_save_and_get_game():
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "white": "A", "black": "B", "result": "1-0", "pgn": "1. e4 *"})
    row = db.get_game(gid)
    assert row["white"] == "A" and row["result"] == "1-0"
    assert db.get_game(9999) is None
    db.close()


def test_db_moves_round_trip():
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": "1. e4 *"})
    db.save_moves(gid, [
        {"ply": 1, "move_san": "e4", "move_uci": "e2e4", "eval_cp": 20, "classification": "Book"},
        {"ply": 2, "move_san": "e5", "move_uci": "e7e5", "eval_cp": 10, "classification": "Book"},
    ])
    moves = db.get_moves(gid)
    assert len(moves) == 2
    assert moves[0]["ply"] == 1 and moves[1]["move_san"] == "e5"
    db.close()


def test_db_dedup_on_chesscom_url():
    db = GameDatabase(":memory:")
    db.save_game({"source": "chesscom", "chesscom_url": "https://chess.com/g/1", "pgn": "*"})
    assert db.game_exists_by_url("https://chess.com/g/1")
    assert not db.game_exists_by_url("https://chess.com/g/2")
    try:
        db.save_game({"source": "chesscom", "chesscom_url": "https://chess.com/g/1", "pgn": "*"})
        raise AssertionError("Expected a UNIQUE constraint violation on duplicate chesscom_url")
    except Exception as e:
        assert "UNIQUE" in str(e).upper() or "unique" in str(type(e).__name__).lower()
    db.close()


def test_db_multiple_null_chesscom_urls_allowed():
    db = GameDatabase(":memory:")
    db.save_game({"source": "local", "chesscom_url": None, "pgn": "*"})
    db.save_game({"source": "local", "chesscom_url": None, "pgn": "*"})
    assert len(db.list_games("local")) == 2
    db.close()


def test_db_favorites_crud():
    db = GameDatabase(":memory:")
    db.set_favorite_status("Ruy Lopez", "study")
    assert db.list_favorites()[0]["favorite_status"] == "study"
    db.set_favorite_status("Ruy Lopez", "master")
    favs = db.list_favorites()
    assert len(favs) == 1 and favs[0]["favorite_status"] == "master"
    assert db.list_favorites("study") == []
    db.close()


def test_db_upsert_opening_result_aggregates():
    db = GameDatabase(":memory:")
    db.upsert_opening_result("C60", "Ruy Lopez", "win")
    db.upsert_opening_result("C60", "Ruy Lopez", "loss")
    db.upsert_opening_result("C60", "Ruy Lopez", "win")
    opening = db.get_opening("Ruy Lopez")
    assert opening["games_played"] == 3
    assert opening["wins"] == 2 and opening["losses"] == 1
    db.close()


def test_db_analytics():
    db = GameDatabase(":memory:")
    db.save_game({"source": "local", "pgn": "*"})
    db.save_game({"source": "local", "pgn": "*"})
    db.upsert_opening_result("C60", "Ruy Lopez", "win")
    db.upsert_opening_result("C60", "Ruy Lopez", "win")
    stats = db.get_analytics()
    assert stats["total_games"] == 2
    assert stats["win_rate"] == 1.0
    assert stats["most_played_opening"]["name"] == "Ruy Lopez"
    db.close()


# ---------------------------------------------------------------------------
# openingbook.py
# ---------------------------------------------------------------------------

def test_openingbook_loads_real_data():
    assert BOOK.line_count > 3000, f"Expected 3000+ named lines, got {BOOK.line_count}"


def test_openingbook_detects_ruy_lopez():
    match = BOOK.detect(["e4", "e5", "Nf3", "Nc6", "Bb5"])
    assert match is not None
    assert match.eco == "C60"
    assert "Ruy Lopez" in match.name
    assert match.ply == 5


def test_openingbook_longest_prefix_wins():
    shallow = BOOK.detect(["e4"])
    deep = BOOK.detect(["e4", "e5", "Nf3", "Nc6", "Bb5"])
    assert deep.ply > shallow.ply


def test_openingbook_no_match_returns_none():
    assert BOOK.detect([]) is None


def test_openingbook_is_book_move():
    so_far = ["e4", "e5", "Nf3", "Nc6"]
    assert BOOK.is_book_move(so_far, "Bb5") is True
    assert BOOK.is_book_move(so_far, "h6") is False


# ---------------------------------------------------------------------------
# moveanalyzer.py — deterministic threshold tests
# ---------------------------------------------------------------------------

STARTING_FEN_WHITE = chess.STARTING_FEN  # white to move


def _classify(played_cp, best_cp=100, eval_before_move=None):
    analyzer = MoveAnalyzer()
    top_moves = [
        {"move": "e2e4", "centipawn": best_cp, "mate": None},
        {"move": "d2d4", "centipawn": played_cp, "mate": None},
    ]
    return analyzer.classify_move(STARTING_FEN_WHITE, "d2d4", top_moves, eval_before_move=eval_before_move)


def test_classify_excellent_boundary():
    c = _classify(played_cp=80)  # cp_loss = 20 (== EXCELLENT_MAX_LOSS)
    assert c.label == LABEL_EXCELLENT, c.label
    assert c.cp_loss == 20


def test_classify_good_just_above_excellent():
    c = _classify(played_cp=79)  # cp_loss = 21
    assert c.label == LABEL_GOOD, c.label


def test_classify_good_boundary():
    c = _classify(played_cp=50)  # cp_loss = 50 (== GOOD_MAX_LOSS)
    assert c.label == LABEL_GOOD, c.label


def test_classify_inaccuracy_boundary():
    c = _classify(played_cp=-40)  # cp_loss = 140
    assert c.label == LABEL_INACCURACY, c.label
    c2 = _classify(played_cp=-50)  # cp_loss = 150 (== INACCURACY_MAX_LOSS)
    assert c2.label == LABEL_INACCURACY, c2.label


def test_classify_mistake_boundary():
    c = _classify(played_cp=-51)  # cp_loss = 151
    assert c.label == LABEL_MISTAKE, c.label
    c2 = _classify(played_cp=-200)  # cp_loss = 300 (== MISTAKE_MAX_LOSS)
    assert c2.label == LABEL_MISTAKE, c2.label


def test_classify_blunder_above_mistake():
    c = _classify(played_cp=-201)  # cp_loss = 301
    assert c.label == LABEL_BLUNDER, c.label


def test_classify_missed_win():
    c = _classify(best_cp=250, played_cp=50)  # winning (>=200) -> drops below 100
    assert c.label == LABEL_MISSED_WIN, c.label


def test_classify_brilliant_requires_eval_before():
    # played move == engine best, recovers from -50 to +300 (>=300 swing)
    analyzer = MoveAnalyzer()
    top_moves = [{"move": "e2e4", "centipawn": 300, "mate": None}]
    c = analyzer.classify_move(STARTING_FEN_WHITE, "e2e4", top_moves, eval_before_move=-50)
    assert c.label == LABEL_BRILLIANT, c.label

    # Same position, but no eval_before_move supplied -> Brilliant never assigned
    c2 = analyzer.classify_move(STARTING_FEN_WHITE, "e2e4", top_moves, eval_before_move=None)
    assert c2.label != LABEL_BRILLIANT


def test_classify_book_move_overrides_eval():
    analyzer = MoveAnalyzer(opening_book=BOOK)
    top_moves = [{"move": "d2d4", "centipawn": 300, "mate": None}]
    c = analyzer.classify_move(
        STARTING_FEN_WHITE, "e2e4", top_moves,
        san_moves_so_far=[], played_san="e4",
    )
    assert c.label == LABEL_BOOK, c.label


def test_classify_mate_scores_handled():
    analyzer = MoveAnalyzer()
    top_moves = [
        {"move": "a", "centipawn": None, "mate": 3},   # White mates in 3
        {"move": "b", "centipawn": -900, "mate": None},  # played move hangs material instead
    ]
    c = analyzer.classify_move(STARTING_FEN_WHITE, "b", top_moves)
    assert c.label in (LABEL_MISSED_WIN, LABEL_BLUNDER), c.label
    assert c.cp_loss > 0


def test_classify_black_to_move_perspective():
    # Black to move: a move that's actually good for Black should not be penalized.
    fen_black = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    analyzer = MoveAnalyzer()
    # White-positive centipawns: -80 is good for Black (best), -10 is worse for Black.
    top_moves = [
        {"move": "e7e5", "centipawn": -80, "mate": None},
        {"move": "a7a6", "centipawn": -10, "mate": None},
    ]
    c = analyzer.classify_move(fen_black, "e7e5", top_moves)
    assert c.is_engine_best is True
    assert c.cp_loss == 0
    assert c.label == LABEL_EXCELLENT


# ---------------------------------------------------------------------------
# pgnhandler.py
# ---------------------------------------------------------------------------

def test_pgn_export_round_trips():
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]:
        board.push_uci(uci)

    exporter = PgnExporter(opening_book=BOOK)
    game = exporter.export_game(board, {"white": "A", "black": "B", "result": "*"})
    assert game.headers["ECO"] == "C60"
    assert "Ruy Lopez" in game.headers["Opening"]

    pgn_text = str(game)
    reparsed = chess.pgn.read_game(io.StringIO(pgn_text))
    assert reparsed.headers["White"] == "A"
    replayed = reparsed.board()
    for node in reparsed.mainline():
        replayed.push(node.move)
    assert replayed.fen() == board.fen()


def test_pgn_export_annotations():
    board = chess.Board()
    board.push_uci("e2e4")
    exporter = PgnExporter(opening_book=BOOK)
    game = exporter.export_game(
        board, {"result": "*"}, move_classifications=[{"classification": "Book"}]
    )
    node = game.variations[0]
    assert node.comment == "Book"


def test_pgn_auto_save_writes_file(tmp_path_str):
    board = chess.Board()
    board.push_uci("e2e4")
    exporter = PgnExporter(opening_book=BOOK, games_dir=tmp_path_str)
    game = exporter.export_game(board, {"result": "*"})
    path = exporter.auto_save(game, game_id=42)
    assert os.path.exists(path)
    assert "42" in os.path.basename(path)


# ---------------------------------------------------------------------------
# chesscom_integration.py — fixture-based (no live network by default)
# ---------------------------------------------------------------------------

SAMPLE_CHESSCOM_PGN = """[Event \"Live Chess\"]
[Site \"Chess.com\"]
[Date \"2026.01.01\"]
[White \"testwhite\"]
[Black \"testblack\"]
[Result \"1-0\"]
[ECO \"C60\"]
[ECOUrl \"https://www.chess.com/openings/Ruy-Lopez-Opening\"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0
"""


def test_chesscom_import_pgn_file(tmp_path_str):
    path = os.path.join(tmp_path_str, "sample.pgn")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE_CHESSCOM_PGN)

    db = GameDatabase(":memory:")
    importer = ChessComImporter()
    summary = importer.import_pgn_file(path, db)
    assert summary.imported == 1 and summary.errors == 0

    games = db.list_games()
    assert games[0]["white"] == "testwhite"
    assert games[0]["eco"] == "C60"
    db.close()


def test_chesscom_game_to_row_parses_opening_from_url():
    importer = ChessComImporter()
    row = importer._game_to_row({"url": "https://chess.com/g/1", "pgn": SAMPLE_CHESSCOM_PGN, "time_control": "600"})
    assert row["chesscom_url"] == "https://chess.com/g/1"
    assert row["opening_name"] == "Ruy Lopez Opening"


def test_chesscom_import_dedup_via_db(tmp_path_str):
    db = GameDatabase(":memory:")
    db.save_game({"source": "chesscom", "chesscom_url": "https://chess.com/g/1", "pgn": "*"})
    importer = ChessComImporter()
    row = importer._game_to_row({"url": "https://chess.com/g/1", "pgn": SAMPLE_CHESSCOM_PGN})
    assert db.game_exists_by_url(row["chesscom_url"])
    db.close()


def test_chesscom_live_import():
    if os.environ.get("RUN_LIVE_NETWORK_TESTS") != "1":
        return  # opt-in only — real chess.com API call
    db = GameDatabase(":memory:")
    importer = ChessComImporter()
    summary = importer.import_user("hikaru", db, months=1)
    assert summary.imported > 0
    db.close()


# ---------------------------------------------------------------------------
# openingtracker.py
# ---------------------------------------------------------------------------

DEVIATION_PGN = """[Event \"Test\"]
[White \"A\"]
[Black \"B\"]
[Result \"*\"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 h6 4. Bxc6 dxc6 *
"""


def test_opening_tracker_finds_first_deviation():
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": DEVIATION_PGN})
    tracker = OpeningMistakeTracker(BOOK)
    result = tracker.analyze_game(gid, db)  # no engine -> deviation found, severity unset
    assert result.deviated is True
    assert result.ply == 6
    assert result.played_move == "h6"
    db.close()


def test_opening_tracker_no_deviation_when_book_ends_naturally():
    # A single well-known book move only — no deviation to find within it.
    pgn = '[Event "Test"]\n[White "A"]\n[Black "B"]\n[Result "*"]\n\n1. e4 *\n'
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": pgn})
    tracker = OpeningMistakeTracker(BOOK)
    result = tracker.analyze_game(gid, db)
    assert result.deviated is False
    db.close()


def test_opening_tracker_severity_with_synthetic_engine():
    class FakeEngine:
        """Deterministic stand-in for ChessEngine.get_best_move_with_evaluation."""
        def __init__(self, before_white_cp, after_white_cp):
            self.before = before_white_cp
            self.after = after_white_cp

        def get_best_move_with_evaluation(self, fen):
            # First call = board_before, second = board_after (in analyze_game's order)
            if not hasattr(self, "_called"):
                self._called = True
                return None, {"eval": self.before, "mate": None}
            return None, {"eval": self.after, "mate": None}

    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": DEVIATION_PGN})
    tracker = OpeningMistakeTracker(BOOK)
    # Black deviates at ply 6 (h6). Evals are White-positive: -30 (~equal)
    # swinging to +400 (huge White edge) means Black's h6 was a disaster.
    fake_engine = FakeEngine(before_white_cp=-30, after_white_cp=400)
    result = tracker.analyze_game(gid, db, engine=fake_engine)
    assert result.severity == SEVERITY_CRITICAL, result.severity
    mistakes = db.get_mistakes()
    assert len(mistakes) == 1 and mistakes[0]["severity"] == SEVERITY_CRITICAL
    db.close()


def test_opening_tracker_sound_deviation_not_logged():
    class FakeEngine:
        def __init__(self):
            self._n = 0
        def get_best_move_with_evaluation(self, fen):
            self._n += 1
            # Deviation cost ~10cp — essentially nothing.
            return (None, {"eval": -30, "mate": None}) if self._n == 1 else (None, {"eval": -40, "mate": None})

    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": DEVIATION_PGN})
    tracker = OpeningMistakeTracker(BOOK)
    result = tracker.analyze_game(gid, db, engine=FakeEngine())
    assert result.severity is None
    assert db.get_mistakes() == []
    db.close()


def test_study_plan_ranks_by_weighted_severity():
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": "*"})
    db.save_mistake({"game_id": gid, "eco": "C60", "severity": SEVERITY_MINOR, "played_move": "h6", "book_move": "Bb4"})
    db.save_mistake({"game_id": gid, "eco": "B01", "severity": SEVERITY_CRITICAL, "played_move": "x", "book_move": "y"})
    tracker = OpeningMistakeTracker(BOOK)
    plan = tracker.study_plan(db, top_n=5)
    assert plan[0]["eco"] == "B01"  # critical (weight 4) outranks a single minor (weight 1)
    db.close()


def test_recommend_favorites_study_and_master():
    db = GameDatabase(":memory:")
    gid = db.save_game({"source": "local", "pgn": "*"})
    db.upsert_opening_result("B01", "Scandinavian Defense", "loss")
    db.save_mistake({"game_id": gid, "eco": "B01", "severity": SEVERITY_CRITICAL})
    db.save_mistake({"game_id": gid, "eco": "B01", "severity": SEVERITY_CRITICAL})

    for _ in range(5):
        db.upsert_opening_result("C60", "Ruy Lopez", "win")

    tracker = OpeningMistakeTracker(BOOK)
    suggestions = {s["name"]: s["suggested_status"] for s in tracker.recommend_favorites(db)}
    assert suggestions.get("Scandinavian Defense") == "study"
    assert suggestions.get("Ruy Lopez") == "master"
    db.close()


# ---------------------------------------------------------------------------
# Integration: play a short local game end-to-end through the real pipeline
# ---------------------------------------------------------------------------

def test_integration_full_pipeline(tmp_path_str):
    board = chess.Board()
    for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:  # Fool's Mate
        board.push_uci(uci)
    assert board.is_checkmate()

    exporter = PgnExporter(opening_book=BOOK, games_dir=tmp_path_str)
    pgn_game = exporter.export_game(board, {"white": "Agent 17", "black": "JARVIS", "result": board.result()})

    db = GameDatabase(":memory:")
    gid = db.save_game({
        "source": "local",
        "white": "Agent 17", "black": "JARVIS",
        "result": pgn_game.headers["Result"],
        "eco": pgn_game.headers.get("ECO"),
        "opening_name": pgn_game.headers.get("Opening"),
        "pgn": str(pgn_game),
        "final_fen": board.fen(),
    })
    path = exporter.auto_save(pgn_game, game_id=gid)
    assert os.path.exists(path)

    stored = db.get_game(gid)
    assert stored["result"] == "0-1"

    reparsed = chess.pgn.read_game(io.StringIO(stored["pgn"]))
    replay_board = reparsed.board()
    sans = []
    for node in reparsed.mainline():
        sans.append(replay_board.san(node.move))
        replay_board.push(node.move)
    match = BOOK.detect(sans)
    assert match is not None and match.name == pgn_game.headers.get("Opening")

    tracker = OpeningMistakeTracker(BOOK)
    tracker.analyze_game(gid, db)  # no assertion on outcome — just must not raise
    plan = tracker.study_plan(db)
    assert isinstance(plan, list)

    db.close()


def main():
    print("=" * 60)
    print("  JARVIS Chess - Tier 1.5 Test Suite")
    print("=" * 60)

    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="jarvis_chess_test_")

    def with_tmp(fn):
        return lambda: fn(tmp_dir)

    tests = [
        ("DB: schema creates all tables", test_db_schema_creates_tables),
        ("DB: save/get game", test_db_save_and_get_game),
        ("DB: moves round-trip", test_db_moves_round_trip),
        ("DB: dedup on chesscom_url", test_db_dedup_on_chesscom_url),
        ("DB: multiple NULL chesscom_url allowed", test_db_multiple_null_chesscom_urls_allowed),
        ("DB: favorites CRUD", test_db_favorites_crud),
        ("DB: opening result aggregation", test_db_upsert_opening_result_aggregates),
        ("DB: analytics", test_db_analytics),
        ("OpeningBook: loads real ECO dataset (3000+)", test_openingbook_loads_real_data),
        ("OpeningBook: detects Ruy Lopez", test_openingbook_detects_ruy_lopez),
        ("OpeningBook: longest prefix wins", test_openingbook_longest_prefix_wins),
        ("OpeningBook: no match -> None", test_openingbook_no_match_returns_none),
        ("OpeningBook: is_book_move", test_openingbook_is_book_move),
        ("MoveAnalyzer: Excellent boundary (cp_loss=20)", test_classify_excellent_boundary),
        ("MoveAnalyzer: Good just above Excellent", test_classify_good_just_above_excellent),
        ("MoveAnalyzer: Good boundary (cp_loss=50)", test_classify_good_boundary),
        ("MoveAnalyzer: Inaccuracy boundary (cp_loss=150)", test_classify_inaccuracy_boundary),
        ("MoveAnalyzer: Mistake boundary (cp_loss=300)", test_classify_mistake_boundary),
        ("MoveAnalyzer: Blunder above Mistake", test_classify_blunder_above_mistake),
        ("MoveAnalyzer: Missed Win", test_classify_missed_win),
        ("MoveAnalyzer: Brilliant requires eval_before_move", test_classify_brilliant_requires_eval_before),
        ("MoveAnalyzer: Book overrides eval-based label", test_classify_book_move_overrides_eval),
        ("MoveAnalyzer: mate scores handled", test_classify_mate_scores_handled),
        ("MoveAnalyzer: Black-to-move perspective", test_classify_black_to_move_perspective),
        ("PgnExporter: export round-trips through chess.pgn", test_pgn_export_round_trips),
        ("PgnExporter: annotations embedded as comments", test_pgn_export_annotations),
        ("PgnExporter: auto_save writes a file", with_tmp(test_pgn_auto_save_writes_file)),
        ("ChessComImporter: import_pgn_file (fixture)", with_tmp(test_chesscom_import_pgn_file)),
        ("ChessComImporter: opening name from ECOUrl", test_chesscom_game_to_row_parses_opening_from_url),
        ("ChessComImporter: dedup via db", with_tmp(test_chesscom_import_dedup_via_db)),
        ("ChessComImporter: live import (opt-in)", test_chesscom_live_import),
        ("OpeningTracker: finds first deviation", test_opening_tracker_finds_first_deviation),
        ("OpeningTracker: no deviation when book ends naturally", test_opening_tracker_no_deviation_when_book_ends_naturally),
        ("OpeningTracker: severity via synthetic engine", test_opening_tracker_severity_with_synthetic_engine),
        ("OpeningTracker: sound deviation not logged as mistake", test_opening_tracker_sound_deviation_not_logged),
        ("OpeningTracker: study plan ranks by weighted severity", test_study_plan_ranks_by_weighted_severity),
        ("OpeningTracker: recommend_favorites study/master", test_recommend_favorites_study_and_master),
        ("Integration: full local-game pipeline", with_tmp(test_integration_full_pipeline)),
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
