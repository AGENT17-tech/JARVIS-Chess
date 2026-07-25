import chess
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class ChessGame:
    """Manages chess game state and move validation."""
    
    def __init__(self):
        """Initialize new game."""
        self.board = chess.Board()
        self.move_history = []
        logger.info("New game initialized")
    
    def reset(self):
        """Reset board to starting position."""
        self.board.reset()
        self.move_history.clear()
        logger.info("Game reset")
    
    def make_move(self, move_uci: str) -> Tuple[bool, str]:
        """
        Attempt to make a move in UCI format.
        
        Args:
            move_uci: Move in UCI format (e.g., 'e2e4')
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Parse UCI move
            move = chess.Move.from_uci(move_uci)
            
            # Validate move is legal
            if move not in self.board.legal_moves:
                return False, f"Illegal move: {move_uci}. Use algebraic notation (e.g., e2e4)"
            
            # Make the move
            self.board.push(move)
            self.move_history.append(move_uci)
            
            # Log move in algebraic notation
            san = self.board.san(self.board.pop())
            self.board.push(move)
            logger.info(f"Move made: {san} ({move_uci})")
            
            return True, f"Move accepted: {san}"
        
        except ValueError as e:
            return False, f"Invalid move format: {move_uci}. Use UCI format (e.g., e2e4)"
        except Exception as e:
            logger.error(f"Move error: {e}")
            return False, f"Error processing move: {e}"
    
    def get_game_status(self) -> dict:
        """
        Get current game state.
        
        Returns:
            Dict with game status info
        """
        status = {
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_check": self.board.is_check(),
            "is_game_over": self.board.is_game_over(),
            "turn": "White" if self.board.turn else "Black",
            "fen": self.board.fen(),
            "move_count": len(self.move_history),
        }
        
        # Determine outcome
        if status["is_checkmate"]:
            loser = "Black" if self.board.turn else "White"
            status["outcome"] = f"Checkmate! {loser} loses."
        elif status["is_stalemate"]:
            status["outcome"] = "Stalemate - Draw"
        elif status["is_game_over"]:
            status["outcome"] = "Game over"
        else:
            status["outcome"] = "Game in progress"
        
        return status
    
    def is_game_over(self) -> bool:
        """Check if game has ended."""
        return self.board.is_game_over()
    
    def get_fen(self) -> str:
        """Get FEN notation of current position."""
        return self.board.fen()
    
    def undo_move(self) -> Tuple[bool, str]:
        """Undo last move."""
        if not self.move_history:
            return False, "No moves to undo"
        
        self.board.pop()
        self.move_history.pop()
        logger.info("Move undone")
        return True, "Last move undone"
    
    def get_legal_moves_uci(self) -> list:
        """Get all legal moves in UCI format."""
        return [move.uci() for move in self.board.legal_moves]
    
    def get_legal_moves_san(self) -> list:
        """Get all legal moves in algebraic notation."""
        moves = []
        for move in self.board.legal_moves:
            moves.append(self.board.san(move))
        return moves
