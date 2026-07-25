import logging
import os
from datetime import datetime
from typing import Optional

import chess
import chess.pgn

from openingbook import OpeningBook

logger = logging.getLogger(__name__)

# JARVIS_GAMES_DIR overrides the default __file__-relative "games" dir. That
# default resolves inside PyInstaller's onefile temp extraction dir when
# frozen, which is wiped between runs — the packaged desktop app sets this
# env var to a persistent per-user data directory instead.
DEFAULT_GAMES_DIR = os.environ.get(
    "JARVIS_GAMES_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "games"),
)


class PgnExporter:
    """Exports a played game (python-chess Board) to standard PGN, with
    optional per-move classification annotations and opening tagging."""

    def __init__(self, opening_book: Optional[OpeningBook] = None, games_dir: str = DEFAULT_GAMES_DIR):
        self.opening_book = opening_book or OpeningBook()
        self.games_dir = games_dir

    def export_game(
        self,
        board: chess.Board,
        metadata: Optional[dict] = None,
        move_classifications: Optional[list] = None,
    ) -> chess.pgn.Game:
        """
        Build a chess.pgn.Game from a finished/in-progress board.

        Args:
            board: python-chess Board whose move_stack holds the played game
                (from the starting position).
            metadata: optional header overrides — white, black, result, date,
                event, round, time_control, eco, opening_name.
            move_classifications: optional list aligned with board.move_stack,
                each entry a dict like {"classification": "Blunder", "cp_loss": 320}
                (any/all keys optional; None entries are skipped).

        Returns:
            A chess.pgn.Game ready to be written out.
        """
        metadata = metadata or {}
        game = chess.pgn.Game.from_board(board)

        game.headers["Event"] = metadata.get("event", "JARVIS Chess")
        game.headers["Site"] = metadata.get("site", "JARVIS-Chess CLI")
        game.headers["Date"] = metadata.get("date", datetime.now().strftime("%Y.%m.%d"))
        game.headers["Round"] = metadata.get("round", "-")
        game.headers["White"] = metadata.get("white", "Agent 17")
        game.headers["Black"] = metadata.get("black", "JARVIS")
        game.headers["Result"] = metadata.get("result", board.result())
        if metadata.get("time_control"):
            game.headers["TimeControl"] = metadata["time_control"]

        eco = metadata.get("eco")
        opening_name = metadata.get("opening_name")
        if not (eco and opening_name):
            san_moves = self._san_moves(board)
            match = self.opening_book.detect(san_moves)
            if match:
                eco = eco or match.eco
                opening_name = opening_name or match.name
        if eco:
            game.headers["ECO"] = eco
        if opening_name:
            game.headers["Opening"] = opening_name

        if move_classifications:
            node = game
            for i, mv in enumerate(board.move_stack):
                node = node.variations[0] if node.variations else None
                if node is None:
                    break
                entry = move_classifications[i] if i < len(move_classifications) else None
                if entry:
                    label = entry.get("classification")
                    cp_loss = entry.get("cp_loss")
                    if label:
                        comment = label
                        if cp_loss is not None:
                            comment += f": -{cp_loss / 100:.2f}" if cp_loss > 0 else f": {cp_loss / 100:.2f}"
                        node.comment = comment

        return game

    @staticmethod
    def _san_moves(board: chess.Board) -> list:
        replay = chess.Board()
        sans = []
        for move in board.move_stack:
            sans.append(replay.san(move))
            replay.push(move)
        return sans

    def save(self, game: chess.pgn.Game, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            exporter = chess.pgn.FileExporter(fh)
            game.accept(exporter)
        logger.info(f"PGN saved to {path}")
        return path

    def auto_save(self, game: chess.pgn.Game, game_id=None) -> str:
        """Writes to games/YYYY-MM-DD_HHMMSS_<id>.pgn, returns the path."""
        os.makedirs(self.games_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        suffix = str(game_id) if game_id is not None else "local"
        filename = f"{timestamp}_{suffix}.pgn"
        path = os.path.join(self.games_dir, filename)
        return self.save(game, path)
