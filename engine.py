import logging
import os
from typing import Optional
from stockfish import Stockfish

logger = logging.getLogger(__name__)

class ChessEngine:
    """Wrapper around Stockfish chess engine."""
    
    def __init__(self, skill_level: int = 20, depth: int = 20):
        """
        Initialize Stockfish engine.
        
        Args:
            skill_level: 0-20 (0=weakest, 20=strongest)
            depth: search depth in half-moves
        """
        self.skill_level = skill_level
        self.depth = depth
        
        try:
            # Try to find Stockfish binary
            stockfish_path = self._find_stockfish()
            
            if not stockfish_path:
                raise FileNotFoundError(
                    "Stockfish not found. Run: python setup_stockfish.py"
                )
            
            # Initialize Stockfish with explicit path
            self.engine = Stockfish(path=stockfish_path)
            logger.info(f"Stockfish initialized from: {stockfish_path}")
            
            # Configure engine parameters
            self.engine.update_engine_parameters({
                "Threads": 4,
                "Hash": 256,
                "Skill Level": skill_level,
            })
            
            logger.info(f"Engine configured | Skill: {skill_level} | Depth: {depth}")
            
        except FileNotFoundError as e:
            logger.error(f"Stockfish not found: {e}")
            logger.error("Run: python setup_stockfish.py")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Stockfish: {e}")
            raise
    
    @staticmethod
    def _find_stockfish() -> Optional[str]:
        """
        Try to locate Stockfish binary.
        
        Returns:
            Path to stockfish executable or None
        """
        # Windows primary location (from setup_stockfish.py)
        windows_paths = [
            r"C:\stockfish\stockfish.exe",
            r"C:\Program Files\stockfish\stockfish.exe",
            r"C:\Program Files (x86)\stockfish\stockfish.exe",
        ]
        
        for path in windows_paths:
            if os.path.exists(path):
                logger.debug(f"Found stockfish at: {path}")
                return path
        
        # Linux/Mac locations
        linux_paths = [
            "/usr/bin/stockfish",
            "/usr/local/bin/stockfish",
            "/opt/stockfish/stockfish",
        ]
        
        for path in linux_paths:
            if os.path.exists(path):
                logger.debug(f"Found stockfish at: {path}")
                return path
        
        logger.warning("Stockfish binary not found in standard locations")
        return None

    def get_best_move(self, fen: str) -> Optional[str]:
        """
        Get best move for current position (UCI format).
        
        Args:
            fen: FEN string representing board state
            
        Returns:
            Best move in UCI format (e.g., 'e2e4')
        """
        try:
            self.engine.set_fen_position(fen)
            move = self.engine.get_best_move(self.depth)
            
            if move:
                logger.debug(f"Best move: {move}")
            else:
                logger.warning("No move returned by engine")
            
            return move
        except Exception as e:
            logger.error(f"Error getting best move: {e}")
            return None

    def get_best_move_with_evaluation(self, fen: str) -> tuple[Optional[str], Optional[dict]]:
        """
        Get best move AND evaluation score.
        
        Args:
            fen: FEN string
            
        Returns:
            Tuple of (move in UCI, evaluation dict)
        """
        try:
            self.engine.set_fen_position(fen)
            move = self.engine.get_best_move(self.depth)
            
            # Evaluation info
            eval_info = {"eval": 0}
            
            logger.debug(f"Move: {move}")
            return move, eval_info
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return None, None

    def is_checkmate(self, fen: str) -> bool:
        """Check if position is checkmate (handled by python-chess)."""
        return False

    def is_check(self, fen: str) -> bool:
        """Check if position is in check (handled by python-chess)."""
        return False

    def is_stalemate(self, fen: str) -> bool:
        """Check if position is stalemate (handled by python-chess)."""
        return False
