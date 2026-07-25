import logging
from dataclasses import dataclass
from typing import Optional

from openingbook import OpeningBook

logger = logging.getLogger(__name__)

# --- Classification thresholds (centipawns lost vs. engine's best move) ---
# Tune these here; see FEATURES_IMPLEMENTATION_GUIDE.md for rationale.
EXCELLENT_MAX_LOSS = 20
GOOD_MAX_LOSS = 50
INACCURACY_MAX_LOSS = 150
MISTAKE_MAX_LOSS = 300
# Above MISTAKE_MAX_LOSS -> Blunder

BRILLIANT_MIN_RECOVERY = 300   # cp swing from bad/equal to good, on the single best move
MISSED_WIN_PRIOR_EVAL = 200    # position was winning by at least this much...
MISSED_WIN_AFTER_EVAL = 100    # ...and the played move drops below this

MATE_SCORE_BASE = 100000       # magnitude used to represent forced mate as a centipawn-equivalent

LABEL_BOOK = "Book"
LABEL_BRILLIANT = "Brilliant"
LABEL_EXCELLENT = "Excellent"
LABEL_GOOD = "Good"
LABEL_INACCURACY = "Inaccuracy"
LABEL_MISTAKE = "Mistake"
LABEL_BLUNDER = "Blunder"
LABEL_MISSED_WIN = "MissedWin"


@dataclass
class MoveClassification:
    label: str
    cp_loss: int          # centipawns lost from the mover's perspective (>=0, except may be negative for Brilliant)
    is_engine_best: bool
    best_move_uci: Optional[str]


def _score_white(entry: dict) -> int:
    """Convert a top-move dict {'centipawn':..,'mate':..} to a single White-positive integer."""
    if entry is None:
        return 0
    mate = entry.get("mate")
    if mate is not None:
        sign = 1 if mate > 0 else -1
        return sign * (MATE_SCORE_BASE - min(abs(mate), 999) * 100)
    return entry.get("centipawn") or 0


class MoveAnalyzer:
    """Classifies a played move into one of 8 categories (Book counts as a 9th
    state layered on top) by comparing it against the engine's candidate moves."""

    def __init__(self, opening_book: Optional[OpeningBook] = None):
        self.opening_book = opening_book

    def classify_move(
        self,
        fen_before: str,
        played_move_uci: str,
        top_moves: list,
        eval_before_move: Optional[int] = None,
        san_moves_so_far: Optional[list] = None,
        played_san: Optional[str] = None,
    ) -> MoveClassification:
        """
        Args:
            fen_before: FEN of the position before the move (turn field used
                to determine mover's perspective).
            played_move_uci: the move actually played, UCI format.
            top_moves: engine's candidate moves at fen_before, from
                ChessEngine.get_top_moves_with_eval() — best move first, each
                {"move": uci, "centipawn": White-positive|None, "mate": White-positive|None}.
            eval_before_move: optional static White-positive eval of fen_before
                itself (not a candidate move's resulting eval). Required only
                to detect Brilliant moves; if omitted, Brilliant is never assigned.
            san_moves_so_far: SAN move list of the game up to (not including)
                this move — required, with played_san and an opening_book, to
                detect Book moves.
            played_san: this move's SAN — see san_moves_so_far.

        Returns:
            MoveClassification
        """
        white_to_move = fen_before.split(" ")[1] == "w"
        mover_sign = 1 if white_to_move else -1

        if (
            self.opening_book is not None
            and san_moves_so_far is not None
            and played_san is not None
            and self.opening_book.is_book_move(san_moves_so_far, played_san)
        ):
            return MoveClassification(LABEL_BOOK, 0, True, top_moves[0]["move"] if top_moves else None)

        best_entry = top_moves[0] if top_moves else None
        best_move_uci = best_entry["move"] if best_entry else None
        is_engine_best = played_move_uci == best_move_uci

        played_entry = next((m for m in top_moves if m.get("move") == played_move_uci), None)
        if played_entry is not None:
            played_val_white = _score_white(played_entry)
        elif top_moves:
            # Played move fell outside the engine's top N — conservatively treat
            # it as at least as bad as the worst move we evaluated.
            worst_val_white = min(_score_white(m) for m in top_moves)
            played_val_white = worst_val_white - 100 * mover_sign
        else:
            played_val_white = 0

        best_val_white = _score_white(best_entry)

        best_mover = best_val_white * mover_sign
        played_mover = played_val_white * mover_sign
        cp_loss = best_mover - played_mover

        # Missed Win: position was clearly winning, and the played move throws it away.
        if best_mover >= MISSED_WIN_PRIOR_EVAL and played_mover < MISSED_WIN_AFTER_EVAL:
            return MoveClassification(LABEL_MISSED_WIN, cp_loss, is_engine_best, best_move_uci)

        # Brilliant: the single best move, and it swings the position from
        # bad/equal to clearly good (requires an external static eval of fen_before).
        if is_engine_best and eval_before_move is not None:
            prior_mover = eval_before_move * mover_sign
            if (best_mover - prior_mover) >= BRILLIANT_MIN_RECOVERY and best_mover > 0:
                return MoveClassification(LABEL_BRILLIANT, cp_loss, True, best_move_uci)

        if cp_loss <= EXCELLENT_MAX_LOSS:
            label = LABEL_EXCELLENT
        elif cp_loss <= GOOD_MAX_LOSS:
            label = LABEL_GOOD
        elif cp_loss <= INACCURACY_MAX_LOSS:
            label = LABEL_INACCURACY
        elif cp_loss <= MISTAKE_MAX_LOSS:
            label = LABEL_MISTAKE
        else:
            label = LABEL_BLUNDER

        return MoveClassification(label, cp_loss, is_engine_best, best_move_uci)
