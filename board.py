import chess
import logging

logger = logging.getLogger(__name__)

class BoardVisualizer:
    """Display chess board in ASCII format."""
    
    # Unicode chess piece symbols
    PIECE_SYMBOLS = {
        'P': '♙',  # White Pawn
        'N': '♘',  # White Knight
        'B': '♗',  # White Bishop
        'R': '♖',  # White Rook
        'Q': '♕',  # White Queen
        'K': '♔',  # White King
        'p': '♟',  # Black Pawn
        'n': '♞',  # Black Knight
        'b': '♝',  # Black Bishop
        'r': '♜',  # Black Rook
        'q': '♛',  # Black Queen
        'k': '♚',  # Black King
    }
    
    @staticmethod
    def display(board: chess.Board, highlight_moves: list = None) -> str:
        """
        Display board in ASCII with optional highlighted squares.
        
        Args:
            board: python-chess Board object
            highlight_moves: list of squares to highlight (for legal moves)
            
        Returns:
            Formatted string representation of board
        """
        if highlight_moves is None:
            highlight_moves = []
        
        output = []
        output.append("\n  ┌─────────────────────────┐")
        
        for rank in range(7, -1, -1):
            output.append(f"{rank + 1} │ ", )
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                
                # Highlight square if in list
                if square in highlight_moves:
                    output[-1] += "● "
                else:
                    if piece:
                        output[-1] += BoardVisualizer.PIECE_SYMBOLS[piece.symbol()] + " "
                    else:
                        output[-1] += "· "
            
            output[-1] += "│"
        
        output.append("  ├─────────────────────────┤")
        output.append("  │ a b c d e f g h │")
        output.append("  └─────────────────────────┘")
        
        return "\n".join(output)

    @staticmethod
    def display_move_history(board: chess.Board) -> str:
        """Display move history in algebraic notation."""
        moves = []
        temp_board = chess.Board()
        
        for move in board.move_stack:
            moves.append(temp_board.san(move))
            temp_board.push(move)
        
        if not moves:
            return "(No moves yet)"
        
        # Format in pairs
        output = []
        for i in range(0, len(moves), 2):
            if i + 1 < len(moves):
                output.append(f"{i//2 + 1}. {moves[i]} {moves[i+1]}")
            else:
                output.append(f"{i//2 + 1}. {moves[i]}")
        
        return "\n".join(output)

    @staticmethod
    def get_legal_move_squares(board: chess.Board) -> list:
        """Get list of destination squares for legal moves."""
        legal_squares = set()
        for move in board.legal_moves:
            legal_squares.add(move.to_square)
        return list(legal_squares)
