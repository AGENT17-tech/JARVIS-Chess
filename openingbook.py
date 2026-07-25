import csv
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_BOOK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "openings")
MOVE_NUMBER_RE = re.compile(r"\d+\.(\.\.)?")


def _pgn_moves_to_san_list(pgn_moves: str) -> list:
    """'1. e4 e5 2. Nf3 Nc6' -> ['e4', 'e5', 'Nf3', 'Nc6']"""
    cleaned = MOVE_NUMBER_RE.sub("", pgn_moves)
    return cleaned.split()


@dataclass
class OpeningMatch:
    eco: str
    name: str
    ply: int  # number of half-moves (SAN tokens) matched


class OpeningBook:
    """
    Loads the lichess-org/chess-openings ECO dataset (bundled as TSV files
    under resources/openings/) and answers opening-detection / book-deviation
    questions via a move-sequence trie. Pure lookup — no DB access.
    """

    _NAME_KEY = "__opening__"  # trie node key holding (eco, name) if this exact path is a named line

    def __init__(self, book_dir: str = DEFAULT_BOOK_DIR):
        self.book_dir = book_dir
        self.trie: dict = {}
        self.eco_names: dict = {}  # eco code -> first name seen for it (for display/lookup)
        self.name_to_moves: dict = {}  # opening name -> SAN move list (for repertoire export)
        self.line_count = 0
        self._load()

    def _load(self):
        if not os.path.isdir(self.book_dir):
            logger.warning(f"Opening book directory not found: {self.book_dir}")
            return

        tsv_files = sorted(f for f in os.listdir(self.book_dir) if f.endswith(".tsv"))
        for filename in tsv_files:
            path = os.path.join(self.book_dir, filename)
            with open(path, encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    eco = row.get("eco", "").strip()
                    name = row.get("name", "").strip()
                    pgn = row.get("pgn", "").strip()
                    if not (eco and name and pgn):
                        continue
                    moves = _pgn_moves_to_san_list(pgn)
                    if not moves:
                        continue
                    self._insert(moves, eco, name)
                    self.eco_names.setdefault(eco, name)
                    self.name_to_moves.setdefault(name, moves)
                    self.line_count += 1

        logger.info(f"OpeningBook loaded {self.line_count} named lines from {self.book_dir}")

    def _insert(self, moves: list, eco: str, name: str):
        node = self.trie
        for move in moves:
            node = node.setdefault(move, {})
        node[self._NAME_KEY] = (eco, name)

    def detect(self, san_moves: list) -> Optional[OpeningMatch]:
        """
        Longest-prefix match: walk san_moves down the trie, remembering the
        deepest node that corresponds to a named line. Returns None if no
        prefix of san_moves matches any known opening.
        """
        node = self.trie
        best: Optional[OpeningMatch] = None
        for ply, move in enumerate(san_moves, start=1):
            if move not in node:
                break
            node = node[move]
            if self._NAME_KEY in node:
                eco, name = node[self._NAME_KEY]
                best = OpeningMatch(eco=eco, name=name, ply=ply)
        return best

    def is_book_move(self, san_moves_so_far: list, next_san: str) -> bool:
        """True if san_moves_so_far + [next_san] is still a prefix of some known line."""
        node = self.trie
        for move in san_moves_so_far:
            if move not in node:
                return False
            node = node[move]
        return next_san in node

    def deepest_book_ply(self, san_moves: list) -> int:
        """How many plies of san_moves stay within the book (0 if the very first move is unknown)."""
        node = self.trie
        ply = 0
        for move in san_moves:
            if move not in node:
                break
            node = node[move]
            ply += 1
        return ply
