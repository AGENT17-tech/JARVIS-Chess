import io
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

import chess.pgn

from database import GameDatabase

logger = logging.getLogger(__name__)

BASE_URL = "https://api.chess.com/pub"
# chess.com asks API consumers to identify themselves with a descriptive UA;
# requests without any UA are sometimes rejected outright.
USER_AGENT = "JARVIS-Chess/1.0 (github.com/AGENT17-tech/JARVIS-Chess)"


@dataclass
class ImportSummary:
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


class ChessComImporter:
    """Fetches games from the chess.com public API (no auth required) and/or
    parses manually-downloaded PGN files, storing everything via GameDatabase."""

    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_json(self, url: str) -> Optional[dict]:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                last_err = e
            except Exception as e:
                last_err = e
            if attempt < self.max_retries:
                time.sleep(1.5 * attempt)
        raise RuntimeError(f"Failed to fetch {url}: {last_err}")

    def fetch_archives(self, username: str) -> list:
        """List of monthly archive URLs for a username, oldest first."""
        data = self._get_json(f"{BASE_URL}/player/{username}/games/archives")
        return data.get("archives", []) if data else []

    def fetch_month(self, archive_url: str) -> list:
        """Raw game dicts (as chess.com returns them) for one archive month."""
        data = self._get_json(archive_url)
        return data.get("games", []) if data else []

    @staticmethod
    def _opening_name_from_eco_url(eco_url: Optional[str]) -> Optional[str]:
        if not eco_url:
            return None
        slug = eco_url.rstrip("/").split("/")[-1]
        return slug.replace("-", " ")

    def _game_to_row(self, raw_game: dict) -> Optional[dict]:
        pgn_text = raw_game.get("pgn")
        if not pgn_text:
            return None
        parsed = chess.pgn.read_game(io.StringIO(pgn_text))
        if parsed is None:
            return None
        headers = parsed.headers
        final_fen = parsed.end().board().fen()
        return {
            "source": "chesscom",
            "chesscom_url": raw_game.get("url"),
            "white": headers.get("White"),
            "black": headers.get("Black"),
            "result": headers.get("Result"),
            "date": headers.get("Date"),
            "time_control": raw_game.get("time_control"),
            "eco": headers.get("ECO"),
            "opening_name": self._opening_name_from_eco_url(headers.get("ECOUrl")),
            "pgn": pgn_text,
            "final_fen": final_fen,
        }

    def import_user(self, username: str, db: GameDatabase, months: Optional[int] = None) -> ImportSummary:
        """
        Import all (or the most recent `months`) archived games for a
        chess.com username into the database. Dedups on chesscom_url.
        """
        summary = ImportSummary()
        archives = self.fetch_archives(username)
        if months:
            archives = archives[-months:]

        for archive_url in archives:
            try:
                games = self.fetch_month(archive_url)
            except RuntimeError as e:
                summary.errors += 1
                summary.error_messages.append(str(e))
                continue

            for raw_game in games:
                url = raw_game.get("url")
                if url and db.game_exists_by_url(url):
                    summary.skipped += 1
                    continue
                row = self._game_to_row(raw_game)
                if row is None:
                    summary.errors += 1
                    summary.error_messages.append(f"Unparseable game: {url}")
                    continue
                try:
                    db.save_game(row)
                    summary.imported += 1
                except Exception as e:
                    summary.errors += 1
                    summary.error_messages.append(str(e))

        logger.info(f"chess.com import for '{username}': {summary}")
        return summary

    def import_pgn_file(self, path: str, db: GameDatabase) -> ImportSummary:
        """Manual fallback: parse a local multi-game PGN file (e.g. a
        chess.com 'download games' export) and store each game."""
        summary = ImportSummary()
        with open(path, encoding="utf-8") as fh:
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                headers = game.headers
                row = {
                    "source": "manual_import",
                    "chesscom_url": headers.get("Link") or None,
                    "white": headers.get("White"),
                    "black": headers.get("Black"),
                    "result": headers.get("Result"),
                    "date": headers.get("Date"),
                    "time_control": headers.get("TimeControl"),
                    "eco": headers.get("ECO"),
                    "opening_name": headers.get("Opening"),
                    "pgn": str(game),
                    "final_fen": game.end().board().fen(),
                }
                if row["chesscom_url"] and db.game_exists_by_url(row["chesscom_url"]):
                    summary.skipped += 1
                    continue
                try:
                    db.save_game(row)
                    summary.imported += 1
                except Exception as e:
                    summary.errors += 1
                    summary.error_messages.append(str(e))
        return summary
