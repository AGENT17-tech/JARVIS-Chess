import React, { useState } from 'react';
import useTheme from '../hooks/useTheme';

const SQUARES = [
  'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
  'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
  'a6', 'b6', 'c6', 'd6', 'e6', 'f6', 'g6', 'h6',
  'a5', 'b5', 'c5', 'd5', 'e5', 'f5', 'g5', 'h5',
  'a4', 'b4', 'c4', 'd4', 'e4', 'f4', 'g4', 'h4',
  'a3', 'b3', 'c3', 'd3', 'e3', 'f3', 'g3', 'h3',
  'a2', 'b2', 'c2', 'd2', 'e2', 'f2', 'g2', 'h2',
  'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
];

const PIECE_UNICODE = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
};

function getPiecesFromFEN(fen) {
  const pieces = {};
  const rows = fen.split(' ')[0].split('/');
  rows.forEach((row, rowIdx) => {
    let col = 0;
    for (const char of row) {
      if (isNaN(char)) {
        pieces[String.fromCharCode(97 + col) + (8 - rowIdx)] = char;
        col++;
      } else {
        col += parseInt(char, 10);
      }
    }
  });
  return pieces;
}

function isLightSquare(square) {
  const col = square.charCodeAt(0) - 97;
  const row = parseInt(square[1], 10);
  return (col + row) % 2 === 1;
}

// Shared by both the click path and the drag-drop path so promotion
// handling can't drift between the two interaction methods.
function toUci(pieces, from, to) {
  const piece = pieces[from];
  const isPromotion = (piece === 'P' && to[1] === '8') || (piece === 'p' && to[1] === '1');
  return from + to + (isPromotion ? 'q' : '');
}

/**
 * Pure display + click/drag routing — `chess` (chess.js) is used ONLY to
 * compute legal destination squares for highlighting; the server
 * (game_engine.py) remains authoritative for the actual position. See
 * App.js.
 *
 * Drag-and-drop uses the browser's native HTML5 DnD API directly rather
 * than a library (react-dnd's published builds don't resolve cleanly under
 * React 19 + webpack — see git history) — for a single piece type on an
 * 8x8 grid, draggable/onDragStart/onDragOver/onDrop is all this needs.
 */
export default function ChessBoard({ chess, position, selectedSquare, onSelectSquare, onMove, disabled }) {
  const { colors } = useTheme();
  const [dragOverSquare, setDragOverSquare] = useState(null);
  const pieces = getPiecesFromFEN(position);
  const legalDestinations = selectedSquare
    ? chess.moves({ square: selectedSquare, verbose: true }).map((m) => m.to)
    : [];

  const attemptMove = (fromSquare, toSquare) => {
    if (disabled || fromSquare === toSquare) return;
    const dests = chess.moves({ square: fromSquare, verbose: true }).map((m) => m.to);
    if (!dests.includes(toSquare)) return;
    onMove(toUci(pieces, fromSquare, toSquare));
  };

  const handleClick = (square) => {
    if (disabled) return;

    if (selectedSquare === square) {
      onSelectSquare(null);
    } else if (selectedSquare) {
      attemptMove(selectedSquare, square);
      onSelectSquare(null);
    } else if (pieces[square]) {
      onSelectSquare(square);
    }
  };

  const handleDragStart = (e, square) => {
    if (disabled || !pieces[square]) {
      e.preventDefault();
      return;
    }
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', square);
  };

  const handleDragOver = (e, square) => {
    if (disabled) return;
    e.preventDefault(); // required for onDrop to fire
    e.dataTransfer.dropEffect = 'move';
    if (dragOverSquare !== square) setDragOverSquare(square);
  };

  const handleDrop = (e, square) => {
    e.preventDefault();
    setDragOverSquare(null);
    if (disabled) return;
    const fromSquare = e.dataTransfer.getData('text/plain');
    if (fromSquare) attemptMove(fromSquare, square);
    onSelectSquare(null);
  };

  return (
    <div style={{ display: 'inline-block', border: `4px solid ${colors.name === 'dark' ? '#555' : '#333'}`, boxShadow: colors.shadow }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 65px)', gap: 0 }} role="grid" aria-label="Chess board">
        {SQUARES.map((square) => {
          const piece = pieces[square];
          const isSelected = selectedSquare === square;
          const isLegalDest = legalDestinations.includes(square);
          let bgColor = isLightSquare(square) ? '#f0d9b5' : '#b58863';
          if (isSelected) bgColor = '#ffeb3b';
          else if (dragOverSquare === square) bgColor = '#90ee90';
          else if (isLegalDest) bgColor = '#aed581';
          const pieceName = piece ? PIECE_UNICODE[piece] : null;

          return (
            <div
              key={square}
              role="gridcell"
              tabIndex={disabled ? -1 : 0}
              aria-label={`${square}${piece ? `, ${pieceName}` : ', empty'}${isSelected ? ', selected' : ''}`}
              onClick={() => handleClick(square)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleClick(square);
                }
              }}
              onDragOver={(e) => handleDragOver(e, square)}
              onDragLeave={() => setDragOverSquare((s) => (s === square ? null : s))}
              onDrop={(e) => handleDrop(e, square)}
              title={square}
              style={{
                width: '65px', height: '65px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '40px', cursor: disabled ? 'default' : 'pointer', backgroundColor: bgColor,
                border: isSelected ? '3px solid gold' : 'none', transition: 'background-color 0.2s',
              }}
            >
              {piece && (
                <div
                  draggable={!disabled}
                  onDragStart={(e) => handleDragStart(e, square)}
                  style={{ cursor: disabled ? 'default' : 'grab', color: '#1a1a1a' }}
                >
                  {pieceName}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
