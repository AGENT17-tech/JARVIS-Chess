import logging
import time
from typing import Optional

import chess

from game import ChessGame
from engine import ChessEngine
from openingbook import OpeningBook
from moveanalyzer import MoveAnalyzer
from pgnhandler import PgnExporter
from database import GameDatabase

logger = logging.getLogger(__name__)

RANKS = range(7, -1, -1)  # board[0] = rank 8 (top), board[7] = rank 1 (bottom) — visual orientation


class GameEngine:
    """
    Pure data/logic game engine for Tier 2: composes ChessGame (move
    validation, game.py — unchanged) with ChessEngine (Stockfish wrapper,
    engine.py — unchanged), layering move classification (moveanalyzer.py)
    and opening detection (openingbook.py) on top. No CLI I/O — everything
    returns data, nothing prints.
    """

    def __init__(
        self,
        skill_level: int = 20,
        depth: int = 10,
        opening_book: Optional[OpeningBook] = None,
        white_name: str = "Agent 17",
        black_name: str = "JARVIS",
    ):
        self._game = ChessGame()
        self._engine = ChessEngine(skill_level=skill_level, depth=depth)
        # Loading the ~3,800-line ECO dataset per GameEngine instance would be
        # wasteful — callers managing many games (GameManager) should build one
        # OpeningBook and inject it into every GameEngine.
        self.opening_book = opening_book or OpeningBook()
        self.move_analyzer = MoveAnalyzer(self.opening_book)
        self.white_name = white_name
        self.black_name = black_name
        self.game_id: Optional[str] = None  # set by the owning GameManager, if any

        self.move_records = []  # [{ply, san, uci, eval_cp, eval_mate, classification, cp_loss}, ...]
        self._san_history = []
        self._top_moves_cache = None  # (fen, n, result) — avoids re-querying Stockfish for the
                                       # same position across a get_best_move() -> move() pairing
        self.move_stats = []  # [{depth, time_ms}, ...] — timing for each get_best_move() call

        logger.info(f"GameEngine started | skill={skill_level} depth={depth}")

    @property
    def board(self) -> chess.Board:
        return self._game.board

    @property
    def chess_game(self) -> ChessGame:
        """Escape hatch to the underlying game.py ChessGame, for callers (like
        tier1_cli.py) that want its exact status/outcome text for full
        behavioral parity with the pre-refactor CLI."""
        return self._game

    def get_legal_moves_uci(self) -> list:
        return self._game.get_legal_moves_uci()

    # ------------------------------------------------------------------
    # Engine queries
    # ------------------------------------------------------------------

    def _get_top_moves(self, fen: str, n: int) -> list:
        if self._top_moves_cache and self._top_moves_cache[0] == fen and self._top_moves_cache[1] >= n:
            return self._top_moves_cache[2][:n]
        # Always fetch at least 3 — cheap insurance so a get_best_move() ->
        # move() pairing on the same position reuses this instead of re-querying.
        fetch_n = max(n, 3)
        result = self._engine.get_top_moves_with_eval(fen, fetch_n)
        self._top_moves_cache = (fen, fetch_n, result)
        return result[:n]

    def get_best_move(self, depth: Optional[int] = None) -> tuple:
        """
        Returns (uci, eval_info) for the current position's best move, WITHOUT
        applying it. eval_info: {"eval": centipawns|None, "mate": moves|None},
        both White-positive. Does not touch move history/classification.
        """
        fen = self._game.get_fen()
        original_depth = self._engine.depth
        override = depth is not None and str(depth) != str(original_depth)
        if override:
            self._engine.engine.set_depth(depth)
        start = time.time()
        try:
            top = self._get_top_moves(fen, 1)
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.move_stats.append({"depth": depth if depth is not None else original_depth, "time_ms": elapsed_ms})
            if override:
                self._engine.engine.set_depth(original_depth)
                self._top_moves_cache = None  # cache was built at a different depth — don't reuse it

        if not top:
            return None, {}
        best = top[0]
        return best["move"], {"eval": best["centipawn"], "mate": best["mate"]}

    def set_depth(self, depth: int):
        """Live-adjusts search depth for all subsequent get_best_move()/move()
        calls (the engine-depth-slider feature) — persists until changed
        again, unlike get_best_move()'s one-off `depth` override."""
        self._engine.depth = depth
        self._engine.engine.set_depth(depth)
        self._top_moves_cache = None  # cache was built at the old depth — don't reuse it

    def get_engine_stats(self) -> dict:
        """Move-timing stats for this game's get_best_move() calls. Node
        counts aren't included — the python-stockfish wrapper this project
        uses doesn't expose them (no UCI `info nodes/nps` passthrough)."""
        if not self.move_stats:
            return {"total_moves": 0, "avg_time_ms": None, "max_time_ms": None, "min_time_ms": None, "avg_depth": None}
        times = [s["time_ms"] for s in self.move_stats]
        depths = [s["depth"] for s in self.move_stats]
        return {
            "total_moves": len(self.move_stats),
            "avg_time_ms": sum(times) / len(times),
            "max_time_ms": max(times),
            "min_time_ms": min(times),
            "avg_depth": sum(depths) / len(depths),
        }

    # ------------------------------------------------------------------
    # Moves
    # ------------------------------------------------------------------

    def move(self, uci: str) -> tuple:
        """
        Validate and apply a move. Returns (bool, message) — matching
        ChessGame.make_move's contract exactly (not a bare bool), so illegal-
        move messages and legal-move listings callers already rely on keep
        working unchanged.
        """
        fen_before = self._game.get_fen()

        top_moves = []
        try:
            top_moves = self._get_top_moves(fen_before, 3)
        except Exception as e:
            logger.warning(f"Could not fetch top moves for classification: {e}")

        success, message = self._game.make_move(uci)
        if not success:
            return success, message

        # Recover the exact SAN of the move just pushed (same technique
        # game.py's make_move uses internally) rather than parsing its message.
        last_move = self._game.board.pop()
        san = self._game.board.san(last_move)
        self._game.board.push(last_move)
        played_uci = last_move.uci()

        classification = self.move_analyzer.classify_move(
            fen_before,
            played_uci,
            top_moves,
            san_moves_so_far=list(self._san_history),
            played_san=san,
        )

        matched = next((m for m in top_moves if m.get("move") == played_uci), None)
        eval_cp = matched.get("centipawn") if matched else None
        eval_mate = matched.get("mate") if matched else None

        # The other candidates from the same top_moves query are otherwise
        # discarded — surface them as "alternatives" for the UI's move-analysis
        # panel instead of throwing away Stockfish work already paid for.
        alt_board = chess.Board(fen_before)
        alternatives = []
        for entry in top_moves:
            entry_uci = entry.get("move")
            if not entry_uci or entry_uci == played_uci:
                continue
            try:
                alt_move = chess.Move.from_uci(entry_uci)
                alt_san = alt_board.san(alt_move)
            except Exception:
                alt_san = entry_uci
            cp = entry.get("centipawn")
            alternatives.append({"san": alt_san, "eval": (cp / 100.0) if cp is not None else None})

        opening_match = self.opening_book.detect(self._san_history + [san])

        ply = len(self.move_records) + 1
        self.move_records.append({
            "ply": ply,
            "san": san,
            "uci": played_uci,
            "eval_cp": eval_cp,
            "eval_mate": eval_mate,
            "eval": (eval_cp / 100.0) if eval_cp is not None else None,
            "classification": classification.label,
            "cp_loss": classification.cp_loss,
            "alternatives": alternatives,
            "eco": opening_match.eco if opening_match else None,
            "opening_name": opening_match.name if opening_match else None,
        })
        self._san_history.append(san)
        self._top_moves_cache = None  # position changed — stale

        return success, message

    def undo(self) -> tuple:
        success, message = self._game.undo_move()
        if success:
            if self.move_records:
                self.move_records.pop()
            if self._san_history:
                self._san_history.pop()
            self._top_moves_cache = None
        return success, message

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def is_game_over(self) -> bool:
        return self._game.is_game_over()

    def get_status(self) -> str:
        board = self._game.board
        if board.is_checkmate():
            return "checkmate"
        if board.is_stalemate():
            return "stalemate"
        if board.is_game_over():
            return "draw"
        return "playing"

    def get_result(self) -> Optional[str]:
        """'white_win' | 'black_win' | 'draw' | None (game still in progress)."""
        if not self._game.is_game_over():
            return None
        result = self._game.board.result()
        return {"1-0": "white_win", "0-1": "black_win", "1/2-1/2": "draw"}.get(result, "draw")

    def get_moves(self) -> list:
        return self.move_records

    def _board_grid(self) -> list:
        board = self._game.board
        grid = []
        for rank in RANKS:
            row = []
            for file in range(8):
                piece = board.piece_at(chess.square(file, rank))
                row.append(piece.symbol() if piece else None)
            grid.append(row)
        return grid

    def get_state(self) -> dict:
        board = self._game.board
        last_record = self.move_records[-1] if self.move_records else None
        return {
            "game_id": self.game_id,
            "fen": board.fen(),
            "board": self._board_grid(),
            "moves": self.move_records,
            "turn": "white" if board.turn else "black",
            "status": self.get_status(),
            "result": self.get_result(),
            "last_move": last_record["uci"] if last_record else None,
            "legal_moves": self._game.get_legal_moves_uci(),
            "evaluation": {
                "eval": last_record["eval"] if last_record else None,
                "mate": last_record["eval_mate"] if last_record else None,
            },
        }

    # ------------------------------------------------------------------
    # Persistence (shared by tier1_cli.py and api_server.py)
    # ------------------------------------------------------------------

    def save_and_export(self, games_dir: Optional[str] = None):
        """
        Save the game to games_db.sqlite and export a PGN. Same logic
        previously duplicated in main.py's _auto_save_game — extracted here
        so every caller (CLI, WebSocket handler, REST /end route) shares one
        implementation. Returns (game_id, pgn_path), or (None, None) if no
        moves have been played.
        """
        if not self.move_records:
            return None, None

        exporter_kwargs = {"opening_book": self.opening_book}
        if games_dir:
            exporter_kwargs["games_dir"] = games_dir
        exporter = PgnExporter(**exporter_kwargs)

        result = self._game.board.result()
        classifications = [{"classification": r["classification"], "cp_loss": r["cp_loss"]} for r in self.move_records]
        pgn_game = exporter.export_game(
            self._game.board,
            metadata={"white": self.white_name, "black": self.black_name, "result": result},
            move_classifications=classifications,
        )

        db = GameDatabase()
        try:
            game_id = db.save_game({
                "source": "local",
                "chesscom_url": None,
                "white": self.white_name,
                "black": self.black_name,
                "result": result,
                "date": pgn_game.headers.get("Date"),
                "time_control": None,
                "eco": pgn_game.headers.get("ECO"),
                "opening_name": pgn_game.headers.get("Opening"),
                "pgn": str(pgn_game),
                "final_fen": self._game.board.fen(),
            })
            db.save_moves(game_id, [
                {
                    "ply": r["ply"], "move_san": r["san"], "move_uci": r["uci"],
                    "eval_cp": r["eval_cp"], "eval_mate": r["eval_mate"],
                    "classification": r["classification"],
                    "is_book": r["classification"] == "Book",
                }
                for r in self.move_records
            ])
            opening_name = pgn_game.headers.get("Opening")
            if opening_name:
                outcome = "win" if result == "1-0" else ("loss" if result == "0-1" else "draw")
                db.upsert_opening_result(pgn_game.headers.get("ECO"), opening_name, outcome)
        finally:
            db.close()

        path = exporter.auto_save(pgn_game, game_id=game_id)
        return game_id, path
