/**
 * TIER 2: JARVIS Chess Desktop UI - React Prototype
 * 
 * Interactive mockup showing:
 * - Chessboard with drag-drop moves
 * - Move history sidebar
 * - Opening stats dashboard
 * - Move analysis panel
 * - Chess.com import workflow
 * 
 * Mock data (no API yet) - just UI/UX demonstration
 * 
 * To run:
 * 1. npx create-react-app tier2-ui
 * 2. npm install chessboard.js chess.js
 * 3. npm install tailwindcss -D
 * 4. Replace src/App.jsx with this file
 * 5. npm start
 */

import React, { useState, useEffect } from 'react';
import './App.css';

// Mock Chess Library (simplified - use real chess.js in production)
const Chess = require('chess.js').Chess;

// ============================================================================
// COMPONENTS
// ============================================================================

/** Chessboard - Interactive board with drag-drop moves */
function ChessboardComponent({ position, onMove, selectedSquare, setSelectedSquare, legalMoves }) {
  const squares = [
    'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
    'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
    'a6', 'b6', 'c6', 'd6', 'e6', 'f6', 'g6', 'h6',
    'a5', 'b5', 'c5', 'd5', 'e5', 'f5', 'g5', 'h5',
    'a4', 'b4', 'c4', 'd4', 'e4', 'f4', 'g4', 'h4',
    'a3', 'b3', 'c3', 'd3', 'e3', 'f3', 'g3', 'h3',
    'a2', 'b2', 'c2', 'd2', 'e2', 'f2', 'g2', 'h2',
    'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
  ];

  const pieceUnicodes = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
  };

  // Parse FEN to get piece positions
  const getPiecesFromFEN = (fen) => {
    const pieces = {};
    const board = fen.split(' ')[0];
    const rows = board.split('/');
    
    rows.forEach((row, rowIdx) => {
      let col = 0;
      for (let char of row) {
        if (isNaN(char)) {
          const square = String.fromCharCode(97 + col) + (8 - rowIdx);
          pieces[square] = char;
          col++;
        } else {
          col += parseInt(char);
        }
      }
    });
    return pieces;
  };

  const pieces = getPiecesFromFEN(position);
  const isLightSquare = (square) => {
    const col = square.charCodeAt(0) - 97;
    const row = parseInt(square[1]);
    return (col + row) % 2 === 1;
  };

  const handleSquareClick = (square) => {
    if (selectedSquare === square) {
      setSelectedSquare(null);
    } else if (selectedSquare && legalMoves.includes(selectedSquare + square)) {
      onMove(selectedSquare + square);
      setSelectedSquare(null);
    } else if (pieces[square]) {
      setSelectedSquare(square);
    } else {
      setSelectedSquare(null);
    }
  };

  return (
    <div className="inline-block border-4 border-gray-800 shadow-lg">
      <div className="grid grid-cols-8 gap-0" style={{ width: '520px', height: '520px' }}>
        {squares.map((square) => {
          const piece = pieces[square];
          const isSelected = selectedSquare === square;
          const isLegal = selectedSquare && legalMoves.includes(selectedSquare + square);
          const isLight = isLightSquare(square);

          return (
            <div
              key={square}
              onClick={() => handleSquareClick(square)}
              className={`flex items-center justify-center text-5xl cursor-pointer transition-all
                ${isLight ? 'bg-amber-100' : 'bg-amber-700'}
                ${isSelected ? 'ring-4 ring-yellow-400' : ''}
                ${isLegal ? 'ring-4 ring-green-400' : ''}
                hover:opacity-80
              `}
              title={square}
            >
              {piece && pieceUnicodes[piece]}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Move History - Sidebar showing all moves */
function MoveHistory({ moves, onSelectMove }) {
  const moveClassColor = (classification) => {
    const colors = {
      'Brilliant': 'text-green-600 font-bold',
      'Excellent': 'text-green-500',
      'Good': 'text-blue-500',
      'Book': 'text-gray-600',
      'Inaccuracy': 'text-yellow-600',
      'Mistake': 'text-orange-600 font-bold',
      'Blunder': 'text-red-600 font-bold',
      'Missed Win': 'text-red-700',
    };
    return colors[classification] || 'text-gray-600';
  };

  const moveClassIcon = (classification) => {
    const icons = {
      'Brilliant': '!!',
      'Excellent': '!',
      'Good': '✓',
      'Book': '📖',
      'Inaccuracy': '?',
      'Mistake': '??',
      'Blunder': '❌',
      'Missed Win': '⚠',
    };
    return icons[classification] || '';
  };

  return (
    <div className="w-64 bg-gray-50 border-l border-gray-300 p-4 overflow-y-auto h-full">
      <h2 className="font-bold text-lg mb-4">Move History</h2>
      
      {moves.length === 0 ? (
        <p className="text-gray-500 text-sm">No moves yet</p>
      ) : (
        <div className="space-y-2">
          {moves.map((moveGroup, idx) => (
            <div key={idx} className="text-sm border-b pb-2">
              <div className="font-bold text-gray-700">{idx + 1}.</div>
              
              {moveGroup.white && (
                <div
                  onClick={() => onSelectMove(idx, 'white')}
                  className="cursor-pointer p-1 hover:bg-yellow-100 rounded"
                >
                  <span className="font-mono text-gray-800">{moveGroup.white.san}</span>
                  <span className={`ml-2 text-xs ${moveClassColor(moveGroup.white.classification)}`}>
                    {moveClassIcon(moveGroup.white.classification)} {moveGroup.white.classification}
                  </span>
                </div>
              )}
              
              {moveGroup.black && (
                <div
                  onClick={() => onSelectMove(idx, 'black')}
                  className="cursor-pointer p-1 hover:bg-yellow-100 rounded ml-4"
                >
                  <span className="font-mono text-gray-800">{moveGroup.black.san}</span>
                  <span className={`ml-2 text-xs ${moveClassColor(moveGroup.black.classification)}`}>
                    {moveClassIcon(moveGroup.black.classification)} {moveGroup.black.classification}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Opening Stats - Dashboard showing opening statistics */
function OpeningStats({ gameData }) {
  const stats = {
    totalGames: 45,
    wins: 28,
    losses: 12,
    draws: 5,
    openings: [
      { name: 'Sicilian Defense', record: '12-5-2', rating: 1850, mistakes: 5, status: 'study' },
      { name: 'Ruy Lopez', record: '8-2-1', rating: 1950, mistakes: 1, status: 'master' },
      { name: 'Italian Game', record: '5-3-1', rating: 1820, mistakes: 2, status: 'master' },
      { name: 'French Defense', record: '1-2-1', rating: 1600, mistakes: 3, status: 'avoid' },
    ],
  };

  const statusColor = {
    'study': 'bg-yellow-100 text-yellow-800',
    'master': 'bg-green-100 text-green-800',
    'avoid': 'bg-red-100 text-red-800',
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Opening Statistics</h2>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{stats.totalGames}</div>
          <div className="text-sm text-gray-600">Total Games</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-green-600">{stats.wins}</div>
          <div className="text-sm text-gray-600">Wins</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{stats.losses}</div>
          <div className="text-sm text-gray-600">Losses</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-gray-600">{Math.round(stats.wins / stats.totalGames * 100)}%</div>
          <div className="text-sm text-gray-600">Win Rate</div>
        </div>
      </div>

      {/* Openings Table */}
      <div className="bg-white rounded-lg border border-gray-300">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b border-gray-300">
            <tr>
              <th className="px-4 py-2 text-left font-bold">Opening</th>
              <th className="px-4 py-2 text-center font-bold">Record</th>
              <th className="px-4 py-2 text-center font-bold">Avg Rating</th>
              <th className="px-4 py-2 text-center font-bold">Mistakes</th>
              <th className="px-4 py-2 text-center font-bold">Status</th>
            </tr>
          </thead>
          <tbody>
            {stats.openings.map((opening, idx) => (
              <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-800">{opening.name}</td>
                <td className="px-4 py-3 text-center font-mono text-gray-700">{opening.record}</td>
                <td className="px-4 py-3 text-center font-mono text-gray-700">{opening.rating}</td>
                <td className="px-4 py-3 text-center">
                  <span className={opening.mistakes > 3 ? 'text-red-600 font-bold' : 'text-gray-600'}>
                    {opening.mistakes}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${statusColor[opening.status]}`}>
                    {opening.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recommendation */}
      <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
        <h3 className="font-bold text-yellow-800">📚 Study Recommendation</h3>
        <p className="text-sm text-yellow-700 mt-2">
          You have <strong>5 opening mistakes in Sicilian Defense</strong>. 
          This is your weakest area. Recommend 10 tactical puzzles to sharpen your Sicilian lines.
        </p>
      </div>
    </div>
  );
}

/** Move Analysis - Sidebar showing detailed move info */
function MoveAnalysis({ selectedMove }) {
  if (!selectedMove) {
    return (
      <div className="w-72 bg-gray-50 border-r border-gray-300 p-4 flex items-center justify-center">
        <p className="text-gray-500 text-sm text-center">Click a move to see analysis</p>
      </div>
    );
  }

  const classificationColor = {
    'Brilliant': 'bg-green-600 text-white',
    'Excellent': 'bg-green-500 text-white',
    'Good': 'bg-blue-500 text-white',
    'Book': 'bg-gray-500 text-white',
    'Inaccuracy': 'bg-yellow-500 text-white',
    'Mistake': 'bg-orange-600 text-white',
    'Blunder': 'bg-red-600 text-white',
  };

  return (
    <div className="w-72 bg-gray-50 border-r border-gray-300 p-4 overflow-y-auto h-full">
      <h2 className="font-bold text-lg mb-4">Move Analysis</h2>

      {/* Classification Badge */}
      <div className={`${classificationColor[selectedMove.classification]} p-3 rounded-lg mb-4 text-center font-bold`}>
        {selectedMove.classification}
      </div>

      {/* Evaluation */}
      <div className="mb-4">
        <div className="text-xs font-bold text-gray-600 mb-1">EVALUATION</div>
        <div className="text-2xl font-mono font-bold text-gray-800">{selectedMove.eval.toFixed(2)}</div>
        <div className="text-xs text-gray-600">
          {selectedMove.eval > 0 ? '⬆ White advantage' : '⬇ Black advantage'}
        </div>
      </div>

      {/* Top Alternatives */}
      <div className="mb-4">
        <div className="text-xs font-bold text-gray-600 mb-2">TOP ALTERNATIVES</div>
        <div className="space-y-1">
          {selectedMove.alternatives.map((alt, idx) => (
            <div key={idx} className="bg-white p-2 rounded text-sm border border-gray-200">
              <span className="font-mono font-bold text-gray-800">{alt.san}</span>
              <span className="float-right font-mono text-gray-600">{alt.eval.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Opening Status */}
      <div className="bg-white p-3 rounded border border-gray-200 text-sm">
        <div className="font-bold text-gray-800 mb-1">Opening Context</div>
        <div className="text-gray-700">
          <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-bold">
            📖 Book Move
          </span>
          <p className="text-xs text-gray-600 mt-2">
            This move is within standard Sicilian Defense theory.
          </p>
        </div>
      </div>

      {/* History */}
      <div className="mt-4 text-xs text-gray-500 border-t pt-3">
        <strong>Recent similar moves:</strong> Played 5 times, won 3, lost 1, drawn 1
      </div>
    </div>
  );
}

/** Import Workflow - Modal for chess.com import */
function ImportWorkflow({ isOpen, onClose, onImport }) {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState('input'); // 'input', 'loading', 'complete'
  const [result, setResult] = useState(null);

  const handleImport = async () => {
    setIsLoading(true);
    setStep('loading');
    
    // Simulate API call
    setTimeout(() => {
      setResult({
        username: username,
        gameFetched: 45,
        gameImported: 45,
        timeRange: '2024-01-01 to 2026-07-25',
      });
      setStep('complete');
      setIsLoading(false);
    }, 2000);
  };

  const handleClose = () => {
    setStep('input');
    setUsername('');
    setResult(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 w-96 shadow-2xl">
        <h2 className="text-2xl font-bold mb-4">Import from Chess.Com</h2>

        {step === 'input' && (
          <>
            <p className="text-gray-600 mb-4">Enter your Chess.Com username to import all your games.</p>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g., khalidwalid17"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleImport}
              disabled={!username}
              className="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              Import Games
            </button>
          </>
        )}

        {step === 'loading' && (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Fetching games from Chess.Com...</p>
          </div>
        )}

        {step === 'complete' && result && (
          <>
            <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-4">
              <p className="font-bold text-green-800">✓ Import Complete</p>
              <p className="text-sm text-green-700 mt-2">
                Successfully imported <strong>{result.gameImported}</strong> games from {result.username}
              </p>
            </div>
            <div className="text-sm text-gray-600 space-y-1 mb-4">
              <p><strong>Time range:</strong> {result.timeRange}</p>
              <p><strong>Games imported:</strong> {result.gameImported}</p>
            </div>
            <button
              onClick={handleClose}
              className="w-full bg-gray-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-gray-700"
            >
              Done
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/** Header - Top bar with controls */
function Header({ onImportClick, turn, status }) {
  const statusText = {
    'playing': `${turn === 'w' ? 'Your' : "JARVIS'"} turn`,
    'checkmate': turn === 'w' ? 'JARVIS Won' : 'You Won!',
    'stalemate': 'Stalemate',
  };

  return (
    <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-4 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-3xl font-bold">♞ JARVIS Chess</h1>
          <div className="text-sm text-gray-300">Tier 2: Desktop UI</div>
        </div>
        
        <div className="flex items-center space-x-6">
          <div className="text-center">
            <div className="text-xs text-gray-400">STATUS</div>
            <div className="font-bold">{statusText[status] || statusText['playing']}</div>
          </div>
          
          <button
            onClick={onImportClick}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-bold text-sm transition"
          >
            📥 Import Chess.Com
          </button>
          
          <button className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded font-bold text-sm transition">
            ⚙️ New Game
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN APP
// ============================================================================

export default function App() {
  const [chess] = useState(() => new Chess());
  const [position, setPosition] = useState(chess.fen());
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [legalMoves, setLegalMoves] = useState([]);
  const [moves, setMoves] = useState([]);
  const [selectedMove, setSelectedMove] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [turn, setTurn] = useState('w');
  const [gameStatus, setGameStatus] = useState('playing');

  // Update legal moves when position changes
  useEffect(() => {
    if (selectedSquare) {
      const movesForSquare = chess.moves({ square: selectedSquare, verbose: true });
      setLegalMoves(movesForSquare.map(m => m.from + m.to));
    }
  }, [selectedSquare, position, chess]);

  // Handle move
  const handleMove = (uci) => {
    try {
      const moveFrom = uci.substring(0, 2);
      const moveTo = uci.substring(2, 4);
      const promotion = uci.length > 4 ? uci[4] : undefined;

      const move = chess.move({
        from: moveFrom,
        to: moveTo,
        promotion: promotion,
      });

      if (move) {
        // User move made
        const userMoveData = {
          san: move.san,
          uci: move.uci,
          eval: -0.34, // Mock evaluation
          classification: ['Book', 'Good', 'Excellent'][Math.floor(Math.random() * 3)],
          alternatives: [
            { san: 'e5', eval: -0.32 },
            { san: 'd5', eval: -0.28 },
            { san: 'Nf6', eval: -0.35 },
          ],
        };

        // Simulate JARVIS response
        const legalMoves = chess.moves({ verbose: true });
        if (legalMoves.length > 0) {
          const jarvisMoveObj = legalMoves[Math.floor(Math.random() * Math.min(5, legalMoves.length))];
          chess.move(jarvisMoveObj);

          const jarvisMoveData = {
            san: jarvisMoveObj.san,
            uci: jarvisMoveObj.uci,
            eval: 0.42,
            classification: ['Excellent', 'Good', 'Book'][Math.floor(Math.random() * 3)],
            alternatives: [
              { san: 'Nc3', eval: 0.38 },
              { san: 'd4', eval: 0.40 },
              { san: 'Nf3', eval: 0.35 },
            ],
          };

          // Update move history
          const moveCount = Math.ceil((moves.length + 1) / 2);
          if (chess.turn() === 'w') {
            setMoves([...moves, { white: userMoveData, black: jarvisMoveData }]);
          } else {
            const lastMove = moves[moves.length - 1];
            setMoves([...moves.slice(0, -1), { ...lastMove, black: userMoveData }]);
            setMoves([...moves, { white: jarvisMoveData }]);
          }

          setPosition(chess.fen());
          setTurn(chess.turn());
          setSelectedSquare(null);
          setSelectedMove(null);

          // Check game status
          if (chess.isCheckmate()) {
            setGameStatus('checkmate');
          } else if (chess.isStalemate()) {
            setGameStatus('stalemate');
          }
        }
      }
    } catch (error) {
      console.error('Invalid move:', error);
    }
  };

  return (
    <div className="w-screen h-screen flex flex-col bg-gray-100">
      <Header onImportClick={() => setImportOpen(true)} turn={turn} status={gameStatus} />

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Move analysis */}
        <MoveAnalysis selectedMove={selectedMove} />

        {/* Center - Board */}
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-6">
          <div>
            <p className="text-sm text-gray-600 text-center mb-2">
              {gameStatus === 'playing' ? (turn === 'w' ? 'Your move' : "JARVIS thinking...") : '✓ Game Over'}
            </p>
            <ChessboardComponent
              position={position}
              onMove={handleMove}
              selectedSquare={selectedSquare}
              setSelectedSquare={setSelectedSquare}
              legalMoves={legalMoves}
            />
          </div>
        </div>

        {/* Right sidebar - Move history */}
        <MoveHistory
          moves={moves}
          onSelectMove={(idx, color) => {
            if (color === 'white' && moves[idx].white) {
              setSelectedMove(moves[idx].white);
            } else if (color === 'black' && moves[idx].black) {
              setSelectedMove(moves[idx].black);
            }
          }}
        />
      </div>

      {/* Bottom - Opening stats (full width) */}
      <div className="border-t border-gray-300 bg-white" style={{ height: '280px', overflow: 'hidden' }}>
        <OpeningStats gameData={{}} />
      </div>

      {/* Import Modal */}
      <ImportWorkflow
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        onImport={(username) => console.log('Import:', username)}
      />
    </div>
  );
}
