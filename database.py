import logging
import os
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)

# JARVIS_DB_PATH lets the packaged desktop app point this at a writable
# per-user data directory instead of the (possibly read-only or ephemeral,
# under PyInstaller) working directory. Unset for the CLI, which keeps the
# existing relative-path behavior.
DEFAULT_DB_PATH = os.environ.get("JARVIS_DB_PATH", "games_db.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    chesscom_url TEXT UNIQUE,
    white TEXT,
    black TEXT,
    result TEXT,
    date TEXT,
    time_control TEXT,
    eco TEXT,
    opening_name TEXT,
    pgn TEXT NOT NULL,
    final_fen TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    move_san TEXT,
    move_uci TEXT,
    fen_before TEXT,
    fen_after TEXT,
    eval_cp INTEGER,
    eval_mate INTEGER,
    classification TEXT,
    is_book INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS openings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eco TEXT,
    name TEXT UNIQUE,
    favorite_status TEXT,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    move_id INTEGER REFERENCES moves(id),
    eco TEXT,
    ply INTEGER,
    severity TEXT,
    eval_before INTEGER,
    eval_after INTEGER,
    played_move TEXT,
    book_move TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS puzzles_solved (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    puzzle_id TEXT NOT NULL,
    correct INTEGER NOT NULL,
    solved_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves(game_id);
CREATE INDEX IF NOT EXISTS idx_mistakes_game_id ON mistakes(game_id);
CREATE INDEX IF NOT EXISTS idx_mistakes_eco ON mistakes(eco);
"""


class GameDatabase:
    """SQLite-backed store for games, moves, opening stats, and opening mistakes."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def init_schema(self):
        """Create tables/indexes if they don't already exist."""
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        logger.info(f"Database schema ready at {self.db_path}")

    def close(self):
        self.conn.close()

    # ---- games -------------------------------------------------------

    def save_game(self, game: dict) -> int:
        """
        Insert a game. Expects keys: source, chesscom_url (optional), white,
        black, result, date, time_control, eco, opening_name, pgn, final_fen.

        Returns the new game id.
        """
        cur = self.conn.execute(
            """
            INSERT INTO games
                (source, chesscom_url, white, black, result, date,
                 time_control, eco, opening_name, pgn, final_fen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game.get("source"),
                game.get("chesscom_url"),
                game.get("white"),
                game.get("black"),
                game.get("result"),
                game.get("date"),
                game.get("time_control"),
                game.get("eco"),
                game.get("opening_name"),
                game.get("pgn"),
                game.get("final_fen"),
            ),
        )
        self.conn.commit()
        game_id = cur.lastrowid
        logger.info(f"Saved game id={game_id} source={game.get('source')}")
        return game_id

    def game_exists_by_url(self, chesscom_url: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM games WHERE chesscom_url = ?", (chesscom_url,)
        ).fetchone()
        return row is not None

    def get_game(self, game_id: int) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return dict(row) if row else None

    def list_games(self, source: Optional[str] = None) -> list:
        if source:
            rows = self.conn.execute(
                "SELECT * FROM games WHERE source = ? ORDER BY id", (source,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM games ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    # ---- moves ---------------------------------------------------------

    def save_moves(self, game_id: int, moves: list):
        """
        Bulk-insert moves for a game. Each entry is a dict with keys:
        ply, move_san, move_uci, fen_before, fen_after, eval_cp, eval_mate,
        classification, is_book.
        """
        rows = [
            (
                game_id,
                m.get("ply"),
                m.get("move_san"),
                m.get("move_uci"),
                m.get("fen_before"),
                m.get("fen_after"),
                m.get("eval_cp"),
                m.get("eval_mate"),
                m.get("classification"),
                1 if m.get("is_book") else 0,
            )
            for m in moves
        ]
        self.conn.executemany(
            """
            INSERT INTO moves
                (game_id, ply, move_san, move_uci, fen_before, fen_after,
                 eval_cp, eval_mate, classification, is_book)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        logger.info(f"Saved {len(rows)} moves for game_id={game_id}")

    def get_moves(self, game_id: int) -> list:
        rows = self.conn.execute(
            "SELECT * FROM moves WHERE game_id = ? ORDER BY ply", (game_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- openings (stats + favorites) ----------------------------------

    def upsert_opening_result(self, eco: str, name: str, result: str):
        """
        Record one game's outcome ('win'|'loss'|'draw') against an opening,
        creating the opening row if needed.
        """
        if not name:
            return
        row = self.conn.execute("SELECT * FROM openings WHERE name = ?", (name,)).fetchone()
        win = 1 if result == "win" else 0
        loss = 1 if result == "loss" else 0
        draw = 1 if result == "draw" else 0
        if row:
            self.conn.execute(
                """
                UPDATE openings
                SET games_played = games_played + 1,
                    wins = wins + ?, losses = losses + ?, draws = draws + ?,
                    eco = COALESCE(eco, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
                """,
                (win, loss, draw, eco, name),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO openings (eco, name, games_played, wins, losses, draws)
                VALUES (?, ?, 1, ?, ?, ?)
                """,
                (eco, name, win, loss, draw),
            )
        self.conn.commit()

    def set_favorite_status(self, name: str, status: str):
        """status: 'study' | 'master' | 'avoid'. Creates the opening row if needed."""
        row = self.conn.execute("SELECT 1 FROM openings WHERE name = ?", (name,)).fetchone()
        if row:
            self.conn.execute(
                "UPDATE openings SET favorite_status = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                (status, name),
            )
        else:
            self.conn.execute(
                "INSERT INTO openings (name, favorite_status) VALUES (?, ?)",
                (name, status),
            )
        self.conn.commit()
        logger.info(f"Opening '{name}' marked as {status}")

    def list_favorites(self, status: Optional[str] = None) -> list:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM openings WHERE favorite_status = ? ORDER BY name", (status,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM openings WHERE favorite_status IS NOT NULL ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_opening(self, name: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM openings WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def list_openings(self) -> list:
        rows = self.conn.execute("SELECT * FROM openings ORDER BY games_played DESC").fetchall()
        return [dict(r) for r in rows]

    # ---- mistakes --------------------------------------------------------

    def save_mistake(self, mistake: dict) -> int:
        """
        Keys: game_id, move_id, eco, ply, severity, eval_before, eval_after,
        played_move, book_move.
        """
        cur = self.conn.execute(
            """
            INSERT INTO mistakes
                (game_id, move_id, eco, ply, severity, eval_before, eval_after,
                 played_move, book_move)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mistake.get("game_id"),
                mistake.get("move_id"),
                mistake.get("eco"),
                mistake.get("ply"),
                mistake.get("severity"),
                mistake.get("eval_before"),
                mistake.get("eval_after"),
                mistake.get("played_move"),
                mistake.get("book_move"),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_mistakes(self, eco: Optional[str] = None) -> list:
        if eco:
            rows = self.conn.execute(
                "SELECT * FROM mistakes WHERE eco = ? ORDER BY created_at", (eco,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM mistakes ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    # ---- puzzles -------------------------------------------------------

    def record_puzzle_result(self, puzzle_id: str, correct: bool):
        self.conn.execute(
            "INSERT INTO puzzles_solved (puzzle_id, correct) VALUES (?, ?)",
            (puzzle_id, 1 if correct else 0),
        )
        self.conn.commit()

    def get_puzzle_stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(correct), 0) AS correct FROM puzzles_solved"
        ).fetchone()
        total, correct = row["total"], row["correct"]
        return {
            "total": total,
            "correct": correct,
            "accuracy": (correct / total) if total else None,
        }

    # ---- analytics ---------------------------------------------------

    def get_analytics(self) -> dict:
        """Aggregate stats: total games, win rate, most-played opening, weakest opening."""
        total_games = self.conn.execute("SELECT COUNT(*) AS c FROM games").fetchone()["c"]

        wins = self.conn.execute(
            "SELECT COALESCE(SUM(wins), 0) AS w, COALESCE(SUM(losses), 0) AS l, "
            "COALESCE(SUM(draws), 0) AS d FROM openings"
        ).fetchone()
        decided = wins["w"] + wins["l"] + wins["d"]
        win_rate = (wins["w"] / decided) if decided else None

        most_played = self.conn.execute(
            "SELECT name, games_played FROM openings ORDER BY games_played DESC LIMIT 1"
        ).fetchone()

        weakest = self.conn.execute(
            """
            SELECT eco, COUNT(*) AS mistake_count
            FROM mistakes
            GROUP BY eco
            ORDER BY mistake_count DESC
            LIMIT 1
            """
        ).fetchone()

        return {
            "total_games": total_games,
            "win_rate": win_rate,
            "most_played_opening": dict(most_played) if most_played else None,
            "weakest_opening_by_mistakes": dict(weakest) if weakest else None,
        }
