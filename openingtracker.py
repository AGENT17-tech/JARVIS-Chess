import io
import logging
from dataclasses import dataclass
from typing import Optional

import chess
import chess.pgn

from database import GameDatabase
from openingbook import OpeningBook

logger = logging.getLogger(__name__)

SEVERITY_MINOR = "Minor"
SEVERITY_LOST_ADVANTAGE = "LostAdvantage"
SEVERITY_CRITICAL = "Critical"

MINOR_MAX_LOSS = 50
LOST_ADVANTAGE_MAX_LOSS = 150
# Above LOST_ADVANTAGE_MAX_LOSS -> Critical

SEVERITY_WEIGHT = {SEVERITY_MINOR: 1, SEVERITY_LOST_ADVANTAGE: 2, SEVERITY_CRITICAL: 4}

STUDY_MIN_CRITICAL_MISTAKES = 2
MASTER_MIN_GAMES = 5
MASTER_MIN_WIN_RATE = 0.7


@dataclass
class DeviationResult:
    deviated: bool
    ply: Optional[int] = None
    eco: Optional[str] = None
    played_move: Optional[str] = None
    book_move: Optional[str] = None
    severity: Optional[str] = None  # None if the deviation was sound (no meaningful eval loss)
    eval_before: Optional[int] = None
    eval_after: Optional[int] = None


class OpeningMistakeTracker:
    """Detects where a game left known opening theory, judges whether that
    deviation cost anything, and rolls results up into a study plan."""

    def __init__(self, opening_book: Optional[OpeningBook] = None):
        self.opening_book = opening_book or OpeningBook()

    def _first_deviation(self, pgn_text: str):
        """Walk a game's mainline; return (ply, san_moves, board_before, board_after,
        deviating_san) for the first move that leaves the opening book, or None
        if the whole game (or all of it that's in the book) matches known theory."""
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return None

        board = game.board()
        san_so_far = []
        ply = 0
        for node in game.mainline():
            move = node.move
            san = board.san(move)
            ply += 1
            if not self.opening_book.is_book_move(san_so_far, san):
                board_before = board.copy()
                board.push(move)
                return ply, san_so_far, board_before, board.copy(), san
            san_so_far.append(san)
            board.push(move)
        return None

    def analyze_game(self, game_id: int, db: GameDatabase, engine=None) -> DeviationResult:
        """
        Finds the first opening-book deviation in a stored game and, if an
        engine is supplied, judges its severity from the real eval swing.
        Logs a `mistakes` row unless the deviation turned out to be sound
        (i.e. didn't actually cost anything measurable).
        """
        game_row = db.get_game(game_id)
        if not game_row:
            return DeviationResult(deviated=False)

        deviation = self._first_deviation(game_row["pgn"])
        if deviation is None:
            return DeviationResult(deviated=False)

        ply, san_so_far, board_before, board_after, played_san = deviation
        match = self.opening_book.detect(san_so_far)
        eco = match.eco if match else game_row.get("eco")

        book_move = self._suggest_book_move(san_so_far)

        result = DeviationResult(
            deviated=True, ply=ply, eco=eco, played_move=played_san, book_move=book_move
        )

        if engine is None:
            return result

        white_to_move = board_before.turn
        mover_sign = 1 if white_to_move else -1

        _, eval_before_info = engine.get_best_move_with_evaluation(board_before.fen())
        _, eval_after_info = engine.get_best_move_with_evaluation(board_after.fen())

        eval_before_white = self._eval_to_white_cp(eval_before_info)
        eval_after_white = self._eval_to_white_cp(eval_after_info)

        # get_evaluation() always normalizes to White-positive regardless of
        # whose turn it is in the given FEN, so both sides use the same sign flip.
        eval_before_mover = eval_before_white * mover_sign
        eval_after_mover = eval_after_white * mover_sign

        loss = eval_before_mover - eval_after_mover
        result.eval_before = eval_before_mover
        result.eval_after = eval_after_mover

        if loss < MINOR_MAX_LOSS:
            result.severity = None  # sound deviation, not a mistake
            return result
        elif loss < LOST_ADVANTAGE_MAX_LOSS:
            severity = SEVERITY_MINOR
        elif eval_before_mover > 100 and eval_after_mover < -100:
            severity = SEVERITY_CRITICAL
        elif loss < 300:
            severity = SEVERITY_LOST_ADVANTAGE
        else:
            severity = SEVERITY_CRITICAL

        result.severity = severity
        db.save_mistake(
            {
                "game_id": game_id,
                "move_id": None,
                "eco": eco,
                "ply": ply,
                "severity": severity,
                "eval_before": eval_before_mover,
                "eval_after": eval_after_mover,
                "played_move": played_san,
                "book_move": book_move,
            }
        )
        return result

    @staticmethod
    def _eval_to_white_cp(eval_info: Optional[dict]) -> int:
        if not eval_info:
            return 0
        if eval_info.get("mate") is not None:
            mate = eval_info["mate"]
            sign = 1 if mate > 0 else -1
            return sign * (10000 - min(abs(mate), 99) * 100)
        return eval_info.get("eval") or 0

    def _suggest_book_move(self, san_so_far: list) -> Optional[str]:
        """One known continuation from this position, for study purposes."""
        node = self.opening_book.trie
        for move in san_so_far:
            if move not in node:
                return None
            node = node[move]
        candidates = [k for k in node.keys() if k != OpeningBook._NAME_KEY]
        return candidates[0] if candidates else None

    def study_plan(self, db: GameDatabase, top_n: int = 5) -> list:
        """
        Ranks openings by mistake frequency x severity. Returns a list of
        dicts: {eco, name, mistake_count, weighted_score, worst_severity,
        suggested_line}.
        """
        mistakes = db.get_mistakes()
        by_eco: dict = {}
        for m in mistakes:
            eco = m.get("eco") or "Unknown"
            entry = by_eco.setdefault(eco, {"count": 0, "score": 0, "worst": None, "book_move": None})
            entry["count"] += 1
            entry["score"] += SEVERITY_WEIGHT.get(m.get("severity"), 1)
            if entry["worst"] is None or SEVERITY_WEIGHT.get(m.get("severity"), 0) > SEVERITY_WEIGHT.get(
                entry["worst"], 0
            ):
                entry["worst"] = m.get("severity")
                entry["book_move"] = m.get("book_move")

        ranked = sorted(by_eco.items(), key=lambda kv: kv[1]["score"], reverse=True)[:top_n]
        plan = []
        for eco, stats in ranked:
            plan.append(
                {
                    "eco": eco,
                    "name": self.opening_book.eco_names.get(eco, eco),
                    "mistake_count": stats["count"],
                    "weighted_score": stats["score"],
                    "worst_severity": stats["worst"],
                    "suggested_line": stats["book_move"],
                }
            )
        return plan

    def recommend_favorites(self, db: GameDatabase) -> list:
        """
        Heuristic favorite suggestions: {name, eco, suggested_status, reason}.
        Doesn't write anything — the caller decides whether to apply them via
        db.set_favorite_status().
        """
        suggestions = []
        for opening in db.list_openings():
            name = opening["name"]
            eco = opening.get("eco")
            games_played = opening["games_played"]

            critical_mistakes = sum(
                1 for m in db.get_mistakes(eco=eco) if m.get("severity") == SEVERITY_CRITICAL
            )
            if critical_mistakes >= STUDY_MIN_CRITICAL_MISTAKES:
                suggestions.append(
                    {
                        "name": name,
                        "eco": eco,
                        "suggested_status": "study",
                        "reason": f"{critical_mistakes} critical opening mistakes logged",
                    }
                )
                continue

            if games_played >= MASTER_MIN_GAMES:
                win_rate = opening["wins"] / games_played
                if win_rate >= MASTER_MIN_WIN_RATE:
                    suggestions.append(
                        {
                            "name": name,
                            "eco": eco,
                            "suggested_status": "master",
                            "reason": f"{win_rate:.0%} win rate over {games_played} games",
                        }
                    )
        return suggestions
