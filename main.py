#!/usr/bin/env python3

import logging
import sys
import time
from game import ChessGame
from engine import ChessEngine
from board import BoardVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('jarvis_chess.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class JarvisChessGame:
    """JARVIS Chess CLI - Agent 17 vs Stockfish."""
    
    def __init__(self, skill_level: int = 20):
        """Initialize game with Stockfish engine."""
        self.game = ChessGame()
        self.engine = ChessEngine(skill_level=skill_level, depth=20)
        self.skill_level = skill_level
        logger.info(f"JARVIS Chess initialized | Skill: {skill_level}")
    
    def display_header(self):
        """Display game header."""
        print("\n" + "="*50)
        print("  JARVIS CHESS - Agent 17 vs Stockfish")
        print(f"  Difficulty: {self.skill_level}/20")
        print("="*50)
        print("\nCommands:")
        print("  move <uci>  - Make move (e.g., 'move e2e4')")
        print("  status      - Show game status")
        print("  undo        - Undo last move")
        print("  help        - Show commands")
        print("  quit        - Exit game")
        print("\n")
    
    def run(self):
        """Main game loop."""
        self.display_header()
        
        while True:
            try:
                # Display board
                print(BoardVisualizer.display(self.game.board))
                
                # Check game status
                status = self.game.get_game_status()
                print(f"\nStatus: {status['outcome']}")
                
                # Game over
                if status['is_game_over']:
                    print("\n🏁 Game Over!")
                    self._show_stats()
                    break
                
                # Agent 17's turn (White)
                if status['turn'] == "White":
                    self._handle_agent_move()
                
                # Check game over again
                if self.game.is_game_over():
                    status = self.game.get_game_status()
                    print(f"\n{status['outcome']}")
                    self._show_stats()
                    break
                
                # JARVIS turn (Black)
                else:
                    self._handle_jarvis_move()
            
            except KeyboardInterrupt:
                print("\n\nGame interrupted.")
                break
            except Exception as e:
                logger.error(f"Game error: {e}")
                print(f"Error: {e}")
    
    def _handle_agent_move(self):
        """Handle Agent 17's move input."""
        print("\n[AGENT-17 MOVE]")
        
        while True:
            user_input = input("> ").strip().lower()
            
            if not user_input:
                continue
            
            # Command: status
            if user_input == "status":
                status = self.game.get_game_status()
                print(f"\nTurn: {status['turn']}")
                print(f"Check: {'Yes' if status['is_check'] else 'No'}")
                print(f"FEN: {status['fen']}")
                print(f"Moves: {status['move_count']}")
                continue
            
            # Command: help
            if user_input in ["help", "?"]:
                print("\nAvailable commands:")
                print("  move <uci>  - Enter move (e.g., 'move e2e4')")
                print("  status      - Show current status")
                print("  undo        - Undo last move")
                print("  quit        - Exit game")
                continue
            
            # Command: undo
            if user_input == "undo":
                success, msg = self.game.undo_move()
                print(f"{msg}")
                if success and len(self.game.move_history) > 0:
                    # Undo JARVIS move too
                    self.game.undo_move()
                    print("JARVIS move also undone")
                break
            
            # Command: quit
            if user_input in ["quit", "exit"]:
                print("Exiting...")
                sys.exit(0)
            
            # Command: move
            if user_input.startswith("move "):
                move_uci = user_input.replace("move ", "").strip()
                success, msg = self.game.make_move(move_uci)
                
                if success:
                    print(f"✓ {msg}")
                    break
                else:
                    print(f"✗ {msg}")
                    print("Legal moves (UCI): " + ", ".join(self.game.get_legal_moves_uci()[:5]))
                    print("(showing first 5)")
    
    def _handle_jarvis_move(self):
        """Handle JARVIS move calculation and execution."""
        print("\n[JARVIS MOVE]")
        
        fen = self.game.get_fen()
        
        # Calculate best move
        print("Thinking...", end="", flush=True)
        start_time = time.time()
        
        move_uci, eval_info = self.engine.get_best_move_with_evaluation(fen)
        elapsed = time.time() - start_time
        
        if not move_uci:
            print("\n✗ Engine error - JARVIS passes")
            return
        
        # Make move
        success, msg = self.game.make_move(move_uci)
        
        if success:
            print(f" Done ({elapsed:.2f}s)")
            print(f"✓ JARVIS plays: {move_uci}")
            
            if eval_info:
                mate_in = eval_info.get('mate')
                if mate_in:
                    print(f"  Evaluation: Mate in {mate_in}")
                else:
                    eval_score = eval_info.get('eval', 0)
                    print(f"  Evaluation: {eval_score}")
        else:
            print(f"\n✗ {msg}")
    
    def _show_stats(self):
        """Display game statistics."""
        print("\n" + "="*50)
        print("  GAME STATISTICS")
        print("="*50)
        print(f"Total moves: {len(self.game.move_history)}")
        print(f"Half-moves: {self.game.board.fullmove_number}")
        print("\nMove history:")
        print(BoardVisualizer.display_move_history(self.game.board))
        print("\n" + "="*50)


def main():
    """Entry point."""
    print("Starting JARVIS Chess...")
    
    # Optional: ask for difficulty
    difficulty = 20
    # user_input = input("Enter difficulty (0-20, default 20): ").strip()
    # if user_input.isdigit():
    #     difficulty = min(20, max(0, int(user_input)))
    
    game = JarvisChessGame(skill_level=difficulty)
    game.run()


if __name__ == "__main__":
    main()
