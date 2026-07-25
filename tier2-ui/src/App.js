import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Chess } from 'chess.js';

import Header from './components/Header';
import ChessBoard from './components/ChessBoard';
import MoveHistoryPanel from './components/MoveHistoryPanel';
import MoveAnalysisPanel from './components/MoveAnalysisPanel';
import OpeningStatsPanel from './components/OpeningStatsPanel';
import ImportModal from './components/ImportModal';
import GameHistoryModal from './components/GameHistoryModal';
import EngineDepthControl from './components/EngineDepthControl';
import EngineStatsPanel from './components/EngineStatsPanel';
import PuzzleMode from './components/PuzzleMode';
import ToastContainer from './components/ToastContainer';
import HelpModal from './components/HelpModal';
import SettingsModal from './components/SettingsModal';
import useTheme from './hooks/useTheme';
import useToast from './hooks/useToast';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts';
import useSettings from './hooks/useSettings';

const API_BASE = 'http://localhost:8002';
const WS_BASE = 'ws://localhost:8002';

export default function App() {
  const { colors, resolvedMode, toggle: toggleTheme } = useTheme();
  const toast = useToast();
  const { settings, updateSettings } = useSettings();

  // `chess` (chess.js) is kept in sync with the server's FEN after every
  // broadcast and used ONLY to compute legal destination squares for
  // highlighting — it is never the source of truth. The server (real
  // python-chess + Stockfish, via game_engine.py) is authoritative for
  // position, move history, evaluation, and classification.
  const [chess] = useState(() => new Chess());
  const [position, setPosition] = useState(chess.fen());
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [moves, setMoves] = useState([]);
  const [selectedMove, setSelectedMove] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [status, setStatus] = useState('connecting');
  const [errorMsg, setErrorMsg] = useState(null);
  const [openingStats, setOpeningStats] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [puzzleOpen, setPuzzleOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [engineDepth, setEngineDepth] = useState(settings.defaultDepth);
  const wsRef = useRef(null);

  const refreshOpeningStats = useCallback(() => {
    fetch(`${API_BASE}/api/openings/stats`)
      .then((r) => r.json())
      .then(setOpeningStats)
      .catch(() => toast.error('Could not load opening statistics — check your connection.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyServerState = useCallback((state) => {
    if (state.fen) {
      chess.load(state.fen);
      setPosition(state.fen);
    }
    if (state.moves) setMoves(state.moves);
    if (state.status) {
      setStatus((prev) => {
        // Opening stats only change in the DB when a game actually ends
        // (GameEngine.save_and_export -> upsert_opening_result) — refetching
        // on every move would just repeat unchanged data.
        if (prev === 'playing' && state.status !== 'playing') refreshOpeningStats();
        return state.status;
      });
    }
  }, [chess, refreshOpeningStats]);

  const startGame = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null; // avoid the old socket's onclose firing "disconnected" after we've already moved on
      wsRef.current.close();
    }
    setStatus('connecting');
    setSelectedMove(null);
    setSelectedSquare(null);
    setErrorMsg(null);
    setMoves([]);
    setEngineDepth(settings.defaultDepth);

    fetch(`${API_BASE}/api/games/new?depth=${settings.defaultDepth}`, { method: 'POST' })
      .then((r) => r.json())
      .then((data) => {
        setGameId(data.game_id);
        applyServerState(data.state);

        const ws = new WebSocket(`${WS_BASE}/ws/game/${data.game_id}`);
        ws.onopen = () => setStatus((s) => (s === 'connecting' ? 'playing' : s));
        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.error) {
            setErrorMsg(msg.error);
            if (msg.state) applyServerState(msg.state);
            return;
          }
          if (msg.depth_set != null) {
            setEngineDepth(msg.depth_set);
            return;
          }
          setErrorMsg(null);
          applyServerState(msg);
        };
        ws.onclose = () => {
          setStatus((s) => {
            // Only 'connecting'/'playing' are non-terminal — don't clobber a
            // legitimate game-over status (checkmate/stalemate/draw) if the
            // socket happens to close after the game already ended.
            if (s !== 'connecting' && s !== 'playing') return s;
            if (s === 'playing') toast.warning('Disconnected from JARVIS backend.');
            return 'disconnected';
          });
        };
        wsRef.current = ws;
      })
      .catch(() => {
        setStatus('disconnected');
        toast.error('Could not reach the JARVIS backend. Is it running?');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applyServerState, settings.defaultDepth]);

  useEffect(() => {
    startGame();
    refreshOpeningStats();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount — startGame/refreshOpeningStats are stable via useCallback

  const sendMove = (uci) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'move', uci }));
    }
  };

  const sendSetDepth = (depth) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'set_depth', depth }));
    }
  };

  const handleImported = () => {
    refreshOpeningStats();
  };

  const shortcuts = useMemo(() => ({
    'ctrl+n': () => startGame(),
    'ctrl+i': () => setImportOpen(true),
    'ctrl+h': () => setHistoryOpen(true),
    'ctrl+p': () => setPuzzleOpen(true),
    '?': () => setHelpOpen(true),
    // Closes whichever dialog is open, topmost-registered first - only one
    // is ever open at a time in normal use.
    escape: () => {
      if (helpOpen) return setHelpOpen(false);
      if (settingsOpen) return setSettingsOpen(false);
      if (puzzleOpen) return setPuzzleOpen(false);
      if (historyOpen) return setHistoryOpen(false);
      if (importOpen) return setImportOpen(false);
    },
  }), [startGame, helpOpen, settingsOpen, puzzleOpen, historyOpen, importOpen]);
  useKeyboardShortcuts(shortcuts);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: colors.bg, color: colors.text }}>
      <Header
        status={status}
        gameId={gameId}
        errorMsg={errorMsg}
        onImportClick={() => setImportOpen(true)}
        onNewGameClick={startGame}
        onHistoryClick={() => setHistoryOpen(true)}
        onPuzzleClick={() => setPuzzleOpen(true)}
        onHelpClick={() => setHelpOpen(true)}
        onSettingsClick={() => setSettingsOpen(true)}
        onThemeToggle={toggleTheme}
        themeMode={resolvedMode}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <MoveAnalysisPanel selectedMove={selectedMove} apiBase={API_BASE} />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '24px' }}>
          <p style={{ fontSize: '13px', color: colors.textSecondary }}>
            {status === 'playing' ? (chess.turn() === 'w' ? 'Your move' : 'JARVIS thinking...') : ''}
          </p>
          <ChessBoard
            chess={chess}
            position={position}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            onMove={sendMove}
            disabled={status !== 'playing'}
          />
          <EngineDepthControl depth={engineDepth} onChange={sendSetDepth} disabled={status !== 'playing'} />
          <EngineStatsPanel apiBase={API_BASE} gameId={gameId} moves={moves} />
        </div>

        <MoveHistoryPanel moves={moves} selectedMove={selectedMove} onSelectMove={setSelectedMove} />
      </div>

      <div style={{ borderTop: `1px solid ${colors.border}`, backgroundColor: colors.cardBg, height: '300px', overflow: 'hidden' }}>
        <OpeningStatsPanel stats={openingStats} />
      </div>

      <ImportModal
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        apiBase={API_BASE}
        onImported={handleImported}
      />
      <GameHistoryModal isOpen={historyOpen} onClose={() => setHistoryOpen(false)} apiBase={API_BASE} />
      <PuzzleMode isOpen={puzzleOpen} onClose={() => setPuzzleOpen(false)} apiBase={API_BASE} />
      <HelpModal isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onUpdate={updateSettings}
      />
      <ToastContainer />
    </div>
  );
}
