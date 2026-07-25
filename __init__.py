"""JARVIS Chess - Tier 1 CLI Foundation"""

__version__ = "1.0.0"
__author__ = "Agent 17"
__email__ = "agent17-tech@github.com"

from .game import ChessGame
from .engine import ChessEngine
from .board import BoardVisualizer

__all__ = ["ChessGame", "ChessEngine", "BoardVisualizer"]
