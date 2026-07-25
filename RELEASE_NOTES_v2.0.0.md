# JARVIS Chess v2.0.0 — Desktop UI Release

## What's New

### Desktop App (Electron)
- Runs as a standalone Windows app (NSIS installer or portable exe) — the
  Electron shell starts the Python/FastAPI backend and manages Stockfish for
  you, no manual setup step.
- Games and opening-stats data are stored per-user under
  `%APPDATA%\JARVIS Chess`, separate from the installed app files.
- Custom app icon and installer branding (taskbar, window, NSIS installer/uninstaller).

### Features
1. **Drag-and-drop board** — move pieces by dragging or by click-to-select;
   both paths share the same legal-move and promotion logic.
2. **Chess.com import** — pull a player's public game history in and store it
   locally for replay and opening analysis.
3. **Game replay** — step through any stored game move-by-move (Start /
   Prev / Next / End, or the `←`/`→` arrow keys) with the board, evaluation
   graph, and move classification all in sync.
4. **Puzzle mode** — solve puzzles pulled live from lichess.org, with a
   running solved/accuracy stat.
5. **Engine depth control** — a 1-20 slider that changes Stockfish's search
   depth for JARVIS's replies mid-game.
6. **Evaluation graph** — a per-move evaluation line chart for any replayed
   game.
7. **Engine performance stats** — move-by-move timing/depth for JARVIS's own
   moves.
8. **Opening statistics** — win/loss/draw record and mistake counts per
   opening, drawn from your actual game history (no placeholder data).

### Polish
- **Dark mode** — light/dark/system, togglable from the header or Settings;
  every panel (board frame excluded, by design) follows the active theme.
- **Settings panel** — pick a default engine depth for new games and set the
  theme in one place; persists across restarts via `localStorage`.
- **Keyboard shortcuts** — `Ctrl+N` new game, `Ctrl+I` import, `Ctrl+H`
  history, `Ctrl+P` puzzles, `←`/`→` to step through a replay, `Esc` to close
  the open dialog, `?` for a shortcut reference.
- **Toast notifications** — connection loss, failed fetches, and failed
  imports surface as dismissible toasts instead of failing silently.
- **Loading states** — spinners for puzzle/game-history fetches instead of a
  blank modal.
- **Accessibility** — ARIA roles/labels throughout (board grid, move list,
  dialogs, live status regions), full keyboard navigation on the board and
  move history, and a visible focus outline across the app.

## How to Use

### Play vs. JARVIS
1. `Ctrl+N` or **New Game**.
2. Drag a piece, or click to select then click a destination.
3. Adjust engine depth with the slider under the board (takes effect on
   JARVIS's next move); set a default for future games in **Settings**.

### Replay a game
1. `Ctrl+H` or **Game History**, then **Replay** on any stored game.
2. Step through with the on-screen controls or `←`/`→`.

### Solve puzzles
1. `Ctrl+P` or **Puzzles**.
2. Play the winning move; **Next Puzzle**/**Skip Puzzle** to continue.

### Import from Chess.com
1. `Ctrl+I` or **Import Chess.com**, enter a username, **Import Games**.

## Keyboard Shortcuts
| Key | Action |
|---|---|
| `Ctrl+N` | New game |
| `Ctrl+I` | Import from Chess.com |
| `Ctrl+H` | Game history |
| `Ctrl+P` | Puzzle mode |
| `←` / `→` | Previous / next move (while replaying a game) |
| `Esc` | Close the open dialog |
| `?` | Show keyboard shortcuts |

## System Requirements
- Windows 10+ (64-bit). No Python install required for the packaged app.

## Known Limitations
- Puzzle difficulty is whatever lichess.org's random-puzzle endpoint returns
  — there's no local difficulty filter yet.
- Engine depth tops out at 20; higher is impractically slow for Stockfish on
  most hardware.

## Under the Hood
- 99 Python tests (`test_tier1.py`, `test_tier1_5.py`, `test_game_engine.py`,
  `test_api_server.py`, `test_websocket.py`) + 6 React tests, all passing.
- `npm run build` compiles clean.

---

Thank you for playing JARVIS Chess.
