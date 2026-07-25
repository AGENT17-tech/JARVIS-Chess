# JARVIS Chess — Tier 2 API Reference

FastAPI backend (`api_server.py`) powering `tier2-ui/`. Start it with
`python main.py serve` (default `http://127.0.0.1:8002`). CORS allows
`http://localhost:3000` and `http://127.0.0.1:3000`.

All game state is held in-memory per process (`GameManager`, module-level
singleton) — restarting the server loses in-progress games. Finished games
are persisted to `games_db.sqlite` + a PGN under `games/` regardless (via
`GameEngine.save_and_export()`), same as the CLI's existing auto-save.

## GameState shape

Returned by every route/WebSocket message that carries game data:

```jsonc
{
  "game_id": "game_592ef7752632",
  "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
  "board": [ ["r","n","b","q","k","b","n","r"], ..., ["R","N","B","Q","K","B","N","R"] ],
  // board[0] = rank 8 (top/Black's back row) ... board[7] = rank 1 (bottom/White's back row)
  "moves": [
    {"ply": 1, "san": "e4", "uci": "e2e4", "eval_cp": 30, "eval_mate": null,
     "eval": 0.30, "classification": "Book", "cp_loss": 0}
  ],
  "turn": "white",                 // "white" | "black"
  "status": "playing",             // "playing" | "checkmate" | "stalemate" | "draw"
  "result": null,                  // null while playing, else "white_win"|"black_win"|"draw"
  "last_move": "e2e4",
  "legal_moves": ["a2a3", "a2a4", ...],
  "evaluation": {"eval": 0.30, "mate": null}   // from the last played move, not a fresh live query
}
```

`classification` is one of: `Book`, `Brilliant`, `Excellent`, `Good`,
`Inaccuracy`, `Mistake`, `Blunder`, `MissedWin` — see Tier 1.5's
`moveanalyzer.py` for the threshold table. `eval`/`eval_cp` are White-positive
(a positive number always favors White, regardless of who moved).

## REST routes

### Games

| Method | Path | Body/Query | Description |
|---|---|---|---|
| POST | `/api/games/new` | query: `skill_level` (default 20), `depth` (default 10) | Creates a game, returns `{game_id, state}` |
| GET | `/api/games/{game_id}/state` | — | Current `GameState` |
| POST | `/api/games/{game_id}/move` | `{"uci": "e2e4"}` | Applies the move, then auto-plays JARVIS's reply if the game isn't over — same behavior as the WebSocket. Returns the resulting `GameState`. 400 if illegal, 404 if unknown game |
| GET | `/api/games/{game_id}/moves` | — | `{"moves": [...]}` |
| POST | `/api/games/{game_id}/end` | — | Saves to DB/PGN and removes the game from the in-memory manager. Returns `{"saved_game_id": int, "pgn_path": str}` |
| GET | `/api/games` | — | `{"games": [{"game_id", "turn", "status", "moves"}, ...]}` for every active game |

```bash
curl -X POST "http://127.0.0.1:8002/api/games/new"
curl -X POST "http://127.0.0.1:8002/api/games/game_abc123/move" -H "Content-Type: application/json" -d '{"uci":"e2e4"}'
curl "http://127.0.0.1:8002/api/games/game_abc123/state"
```

### Openings

| Method | Path | Body/Query | Description |
|---|---|---|---|
| GET | `/api/openings/stats` | — | `{"analytics": {...}, "openings": [...]}` — see `database.py`'s `get_analytics()`/`list_openings()` |
| GET | `/api/openings/{eco}/analysis` | — | Aggregated stats + logged mistakes for one ECO code (an ECO can map to several named lines) |
| POST | `/api/openings/{opening}/favorite` | `{"status": "study"\|"master"\|"avoid"}` | Marks an opening (by name) in your repertoire. 400 on an invalid status |

```bash
curl "http://127.0.0.1:8002/api/openings/stats"
curl "http://127.0.0.1:8002/api/openings/C60/analysis"
curl -X POST "http://127.0.0.1:8002/api/openings/Ruy%20Lopez/favorite" -H "Content-Type: application/json" -d '{"status":"study"}'
```

### Import

| Method | Path | Body/Query | Description |
|---|---|---|---|
| POST | `/api/import/chesscom/{username}` | query: `months` (optional) | Imports a chess.com user's public games. `{"imported", "skipped", "errors", "error_messages"}` |
| POST | `/api/import/pgn` | multipart file upload, field `file` | Imports every game in an uploaded multi-game PGN file |

```bash
curl -X POST "http://127.0.0.1:8002/api/import/chesscom/hikaru?months=1"
curl -X POST "http://127.0.0.1:8002/api/import/pgn" -F "file=@mygames.pgn"
```

## WebSocket `/ws/game/{game_id}`

On connect, the server immediately sends the current `GameState`. After that:

**Client -> server** (JSON):
```jsonc
{"action": "move", "uci": "e2e4"}
{"action": "undo"}
```

**Server -> client** (JSON), one of:
- A `GameState` (broadcast to every connection on this `game_id`) after a move or undo succeeds.
  If the move ended the game, the state additionally carries
  `"saved": {"game_id": <db id>, "pgn_path": "games/....pgn"}`.
- `{"error": "<message>"}` — for an unknown action.
- `{"error": "<message>", "state": <GameState>}` — for an illegal move; sent **only to the
  connection that sent it**, and nothing is broadcast (the game didn't change).

`undo` unwinds both the player's last move and JARVIS's reply together (if both exist) —
same semantics as the CLI's `undo` command.

The player's move ending the game (checkmate/stalemate) is checked **before** JARVIS's reply is
computed — no move is attempted for an already-finished game.

## Known limitations

- **In-memory only.** No game persists across a server restart until it ends (or `/end` is
  called explicitly).
- **One Stockfish process per active game.** `GameEngine` spins up a real `stockfish` subprocess
  per game; many concurrent games means many subprocesses. Fine for local/dev use; would need a
  pooling strategy for anything bigger.
- **Move latency is real Stockfish search time**, not a fixed constant — see `TIER_2_SETUP.md`
  for measured numbers and why "sub-100ms" isn't achievable once real analysis is in the loop.
