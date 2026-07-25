# Tier 2 UI Expansion

`tier2-ui/src/App.js` grew from a board + move-history-only prototype into the full
dashboard sketched in `TIER_2_PROTOTYPE.jsx`: opening stats, move analysis, and a
chess.com import modal, all wired to the real backend (`api_server.py`).

## What changed

```
tier2-ui/src/App.js                          orchestrator: state, WebSocket, data fetching, composition
tier2-ui/src/components/Header.js             title/status/Import button + a real "New Game" button
tier2-ui/src/components/ChessBoard.js         extracted, same click/highlight logic as before
tier2-ui/src/components/MoveHistoryPanel.js   extracted, now passes the full move record on click
tier2-ui/src/components/MoveAnalysisPanel.js  NEW — left sidebar
tier2-ui/src/components/OpeningStatsPanel.js  NEW — bottom panel
tier2-ui/src/components/ImportModal.js        NEW — chess.com import workflow
tier2-ui/src/App.test.js                      updated for the new composition

game_engine.py       move() now also records `alternatives`, `eco`, `opening_name` per move
api_server.py         openings_stats() now merges a per-opening `mistake_count`
```

No new npm dependencies were added.

## Two assumptions in the original spec that didn't hold

**"No backend changes needed" wasn't quite true.** Three sub-features the prototype
shows had no real data source:

- *Top 3 alternatives per move* — `GameEngine.move()` already fetched the top-3
  candidate moves for classification purposes but discarded everything except the
  played move's own eval. Fixed by keeping the other 2 candidates as `alternatives`
  (`[{san, eval}]`) on each move record.
- *"You've played this line N times" opening record* — nothing tagged a move with
  which opening/ECO it belonged to. Fixed by tagging each move record with
  `eco`/`opening_name` (via `OpeningBook.detect()`, same call `pgnhandler.py` already
  makes at the game level, just per-move here). The UI then calls the *existing*
  `GET /api/openings/{eco}/analysis` route on demand when a book move is selected.
- *Per-opening mistake count in the table* — `/api/openings/stats` returned opening
  rows with no mistake count each. Fixed by grouping `get_mistakes()` by ECO once per
  request and merging a `mistake_count` field onto each row.

All three are additive dict keys on existing response shapes — no route signatures
changed, nothing existing broke (`test_game_engine.py`/`test_api_server.py`'s prior
assertions still pass unmodified; new assertions were added alongside). The
alternative was fabricating plausible-looking numbers client-side, which would have
been the first fake data point introduced anywhere in this project — every other
piece has been real Stockfish/DB output or nothing.

**Tailwind isn't actually wired up.** `TIER_2_PROTOTYPE.jsx` is written entirely in
Tailwind utility classes, but `tailwind.config.js`/`postcss.config.js` don't exist in
`tier2-ui/`, and there's no `index.css`/`App.css` with `@tailwind` directives —
`tailwindcss`/`postcss`/`autoprefixer` are installed as devDependencies but never
configured (the prototype's own `import './App.css'` doesn't even resolve — that file
doesn't exist). Copying the prototype's classNames as-is would render completely
unstyled. All 6 new/extracted components use inline styles instead — same visual
design (colors, spacing, layout, badge colors), translated 1:1 from the prototype's
Tailwind classes, using the same approach the previous session's `App.js` already used
and verified working in a browser.

## Data flow

- `moves` (from WebSocket broadcasts) already carries everything
  `MoveAnalysisPanel` needs per move — clicking a move in `MoveHistoryPanel` passes
  the real object straight through, no extra fetch.
- `openingStats` is fetched once on mount, again whenever `status` transitions away
  from `'playing'` (a game just ended — the only time `upsert_opening_result` runs),
  and again after a successful import. It is **not** refetched on every move, since
  the underlying DB rows don't change until one of those three moments.
- `MoveAnalysisPanel`'s per-opening record (`GET /api/openings/{eco}/analysis`) is
  fetched only when a *book* move (one with a non-null `eco`) is newly selected.

## Verification

```bash
python test_game_engine.py   # 15/15 (was 14, +1 for alternatives/eco/opening_name)
python test_api_server.py    # 17/17 (was 16, +1 for mistake_count)
python test_tier1.py         # 8/8, unaffected
python test_tier1_5.py       # 38/38, unaffected
python test_websocket.py     # 8/8, unaffected

cd tier2-ui
npm run build                # compiles clean
npx react-scripts test --watchAll=false   # 6/6
```

Manual: `python main.py serve` + `npm start`, played live in a browser via
chrome-devtools — moved a piece, clicked it in history, confirmed the analysis panel
showed real classification/eval/alternatives and (for book moves) the opening's
actual record; confirmed the opening-stats panel populated after a game ended.
