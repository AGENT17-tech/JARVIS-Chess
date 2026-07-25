# Move Reference - UCI Format

All moves are entered in **UCI (Universal Chess Interface)** format: `<from><to>[promotion]`

## Common Opening Moves

### King's Pawn Opening
```
move e2e4    # e4 - Most popular opening
move c7c5    # c5 - Sicilian Defense response
```

### Closed Game
```
move d2d4    # d4 - Closed/positional
move d7d5    # d5 - Symmetric response
```

### Ruy Lopez (Spanish)
```
move e2e4
move e7e5
move g1f3    # Knight from g1 to f3
move b8c6    # Knight from b8 to c6
move f1b5    # Bishop from f1 to b5
```

## Piece Movement Format

### Pawns
- Forward: `move e2e4` (e-pawn 2 squares)
- Capture: `move e4d5` (e4 pawn captures on d5)
- Promotion: `move e7e8q` (pawn to e8, promote to queen)
  - `q` = Queen, `r` = Rook, `b` = Bishop, `n` = Knight

### Knights
- From: `move g1f3` (knight from g1 to f3)
- From: `move b8c6` (knight from b8 to c6)

### Bishops
- From: `move f1c4` (bishop from f1 to c4)
- From: `move c8f5` (bishop from c8 to f5)

### Rooks
- From: `move a1a4` (rook from a1 to a4)
- From: `move h8h1` (rook from h8 to h1)

### Queens
- From: `move d1h5` (queen from d1 to h5)
- From: `move d8a5` (queen from d8 to a5)

### Kings
- From: `move e1g1` (king-side castling: king from e1 to g1)
- From: `move e8c8` (queen-side castling: king from e8 to c8)

## Board Coordinates

```
  a b c d e f g h
8 ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜ 8
7 ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟ 7
6 · · · · · · · · 6
5 · · · · · · · · 5
4 · · · · · · · · 4
3 · · · · · · · · 3
2 ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙ 2
1 ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖ 1
  a b c d e f g h
```

**Columns (files):** a, b, c, d, e, f, g, h  
**Rows (ranks):** 1-8 (1=white's back rank, 8=black's back rank)

## Example Game

```
Starting position:
move e2e4          → e4 (king's pawn)
[JARVIS: c7c5]     ← c5 (Sicilian)

move g1f3          → Nf3 (knight)
[JARVIS: d7d6]     ← d6

move d2d4          → d4 (pawn)
[JARVIS: c5d4]     ← cxd4 (pawn capture)

move f3d4          → Nxd4 (knight recapture)
```

## Quick Validation

Before entering a move, verify:
1. **Source square exists**: (a-h, 1-8)
2. **Destination square exists**: (a-h, 1-8)
3. **You own the piece** on the source square
4. **The move is legal** (check JARVIS output for suggestions)

Example error messages:
```
✗ Illegal move: e4e5. Use algebraic notation (e.g., e2e4)
✗ Invalid move format: e2 to e4. Use UCI format (e.g., e2e4)
```

## Commands

```
move <uci>         Make a move (e.g., 'move e2e4')
status             Show position info
undo               Undo last move
help               Show commands
quit               Exit game
```

## Tips

- If unsure of your move, type `status` to see the current position
- Use `undo` to retry moves
- Type the full source→destination (e.g., `g1f3` not just `f3`)
- Castling: just move the king normally (`e1g1` or `e1c1`)
