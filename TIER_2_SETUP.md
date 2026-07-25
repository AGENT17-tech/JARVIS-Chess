# Tier 2 Setup — Backend + UI Together

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

Adds `fastapi`, `uvicorn[standard]`, and `python-multipart` to Tier 1/1.5's existing
`python-chess`/`stockfish`. Nothing else changes — Stockfish still needs to be
installed and on PATH exactly as Tier 1 required (`python setup_stockfish.py` if not).

## 2. Start the backend

```bash
python main.py serve
# -> Starting Tier 2 API server on http://127.0.0.1:8002
```

Options: `python main.py serve --host 0.0.0.0 --port 8002 --reload` (`--reload` is
development-only — auto-restarts on code changes, don't use it in anything resembling
production).

Verify it's up:

```bash
curl http://127.0.0.1:8002/
# {"service":"JARVIS Chess API","status":"ok","active_games":0}
```

## 3. Start the frontend

```bash
cd tier2-ui
npm install   # first time only
npm start
```

Opens `http://localhost:3000`. `App.js` creates a game via `POST /api/games/new` on load
and connects a WebSocket to `/ws/game/{game_id}` — you're playing against the real
Stockfish-backed `GameEngine`, not the earlier client-side mock (which picked a random
move from chess.js's top-5 legal moves and never talked to a backend at all).

## 4. Play

Click a piece (legal destinations highlight green), click a destination — your move and
JARVIS's reply both appear in the move list with real SAN, evaluation, and classification
(Book/Excellent/Blunder/etc., from `moveanalyzer.py`). Finishing a game (checkmate/
stalemate/draw) auto-saves it to `games_db.sqlite` and exports a PGN to `games/`, same as
the CLI.

## Desktop app (Electron)

Instead of running the backend and `npm start` separately, `tier2-ui` can run as a
standalone desktop app that launches the backend for you.

```bash
cd tier2-ui
npm install         # first time only — pulls in electron/electron-builder
npm run electron-dev
```

This starts the CRA dev server, waits for it, then opens an Electron window that spawns
`python main.py serve` itself (see `public/electron.js`). The backend's DB and PGN output
are redirected to `app.getPath('userData')` (e.g. `%APPDATA%\tier2-ui\`) via the
`JARVIS_DB_PATH`/`JARVIS_GAMES_DIR` env vars (see `database.py`/`pgnhandler.py`), instead
of wherever `npm run electron-dev` happens to be invoked from.

### Building the installer

```bash
cd tier2-ui
npm run electron-build
```

Runs, in order: the CRA production build, `build_backend.py` (PyInstaller-bundles
`main.py` into `resources/backend/jarvis-backend.exe` and copies a Stockfish binary in
next to it — see `backend.spec`), then `electron-builder --win`. Output lands in
`tier2-ui/dist/`: an NSIS installer and a portable `.exe`. Neither requires Python or
Stockfish to be installed on the target machine.

`build_backend.py` looks for Stockfish at `C:\stockfish\stockfish.exe` by default (same
place `setup_stockfish.py` puts it) — override with the `STOCKFISH_SRC` env var if yours
lives elsewhere. If it's not found, the build still succeeds but JARVIS won't be able to
move in the packaged app.

### Releasing a build (GitHub Actions)

`.github/workflows/release.yml` runs the full test suite, then `npm run electron-build`,
on every pushed tag matching `v*`, and attaches the resulting `.exe` files to a GitHub
Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Measured move latency (this machine)

The original spec targeted "<100ms WebSocket latency," which isn't achievable once real
Stockfish search is in the loop — every move round-trip involves the player's move
evaluation *and* JARVIS's own move search, each with a 3-move classification query.
Measured end-to-end (`POST`/WebSocket `move` -> broadcast received back), single game,
skill level 20:

| Engine depth | Round-trip |
|---|---|
| 10 (API default) | ~220ms |
| 15 | ~1.2s |
| 20 (Tier 1 CLI's depth) | ~9.3s |

`GameEngine`/`/api/games/new` default to **depth 10** for responsiveness — pass a higher
`depth` when creating a game for stronger (slower) play:

```bash
curl -X POST "http://127.0.0.1:8002/api/games/new?depth=18"
```

`tier1_cli.py` (the terminal game) still defaults to depth 20, unchanged from Tier 1 —
CLI play has no latency pressure the way a live browser UI does.

## Scaling caveats (local/dev tool, not a production deployment)

- **In-memory `GameManager`** — active games live in a single process's memory. A server
  restart loses anything not yet finished (finished games are already safe in the DB).
- **One Stockfish subprocess per active game.** Each `GameEngine` spawns a real
  `stockfish` process. Fine for a handful of concurrent games on a dev machine; would need
  process pooling for anything larger.
- Blocking Stockfish/DB calls inside the WebSocket handler are offloaded via
  `starlette.concurrency.run_in_threadpool` so one game's engine "thinking" time doesn't
  stall other connections' event-loop turns, but they still hold up that connection's own
  request for as long as the engine takes.

## Running the test suites

```bash
python test_tier1.py        # 8/8  — unaffected by the Tier 2 refactor
python test_tier1_5.py      # 38/38
python test_game_engine.py  # GameEngine unit tests
python test_api_server.py   # REST route tests (FastAPI TestClient, no live server needed)
python test_websocket.py    # WebSocket flow tests (TestClient, no live server needed)
```
