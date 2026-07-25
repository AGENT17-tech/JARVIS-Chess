import { render, screen, waitFor, cleanup } from '@testing-library/react';
import App from './App';
import { ThemeProvider } from './hooks/useTheme';
import { ToastProvider } from './hooks/useToast';

// App.js reads theme/toast state via useTheme()/useToast(), which throw
// without their provider ancestors — every render(<App />) below is wrapped
// the same way index.js wraps it for real.
function AllProviders({ children }) {
  return (
    <ThemeProvider>
      <ToastProvider>{children}</ToastProvider>
    </ThemeProvider>
  );
}
const renderApp = () => render(<App />, { wrapper: AllProviders });

// App.js calls fetch()/opens a WebSocket unconditionally on mount — mock both
// so tests run without a live backend, matching the Python test suites'
// convention of not depending on a running server process.
beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (url.includes('/api/games/new')) {
      return Promise.resolve({
        json: () => Promise.resolve({
          game_id: 'game_test123',
          state: {
            fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            moves: [], status: 'playing', turn: 'white',
          },
        }),
      });
    }
    if (url.includes('/api/openings/stats')) {
      return Promise.resolve({
        json: () => Promise.resolve({
          analytics: { total_games: 0, win_rate: null, most_played_opening: null, weakest_opening_by_mistakes: null },
          openings: [],
        }),
      });
    }
    return Promise.resolve({ json: () => Promise.resolve({}) });
  });

  global.WebSocket = jest.fn().mockImplementation(() => ({
    close: jest.fn(),
    send: jest.fn(),
    readyState: 1,
  }));
  global.WebSocket.OPEN = 1;
});

afterEach(() => {
  cleanup();
  jest.restoreAllMocks();
});

test('renders the header title', async () => {
  renderApp();
  expect(await screen.findByText(/JARVIS Chess/i)).toBeInTheDocument();
});

test('creates a game and opens a WebSocket on mount', async () => {
  renderApp();
  await waitFor(() => {
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/games/new'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(global.WebSocket).toHaveBeenCalledWith(expect.stringContaining('/ws/game/game_test123'));
  });
});

test('shows the move-analysis placeholder before any move is selected', async () => {
  renderApp();
  expect(await screen.findByText(/Click a move to see analysis/i)).toBeInTheDocument();
  // Let the mount-time openings-stats fetch settle before this test ends —
  // otherwise its pending promise can resolve during the *next* test's
  // render, updating this (already-unmounted) tree at an awkward moment.
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/openings/stats')));
});

test('shows the opening-stats panel once stats resolve', async () => {
  renderApp();
  await waitFor(() => expect(screen.getByText(/Opening Statistics/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getByText(/No openings recorded yet/i)).toBeInTheDocument());
});

test('renders all 64 board squares', async () => {
  renderApp();
  await waitFor(() => {
    const squares = document.querySelectorAll('[role="gridcell"]');
    expect(squares.length).toBe(64);
  });
});

test('the New Game button starts a fresh game (fetch called again)', async () => {
  const { default: userEvent } = await import('@testing-library/user-event');
  renderApp();
  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  const callsBefore = global.fetch.mock.calls.length;

  await userEvent.click(await screen.findByText(/New Game/i));

  await waitFor(() => expect(global.fetch.mock.calls.length).toBeGreaterThan(callsBefore));
});
