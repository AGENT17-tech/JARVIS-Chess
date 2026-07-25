# JARVIS Chess — Tier 1.5 Features Guide

PGN export, chess.com import, move classification, and opening
detection/tracking, built on top of the Tier 1 CLI. Nothing here changes how
`python main.py` (no arguments) behaves — it's still the same interactive
Agent 17 vs Stockfish game.

## Setup

No new third-party dependencies. Everything added uses the standard library
(`sqlite3`, `urllib.request`) plus `chess.pgn`, already available via the
`python-chess` package Tier 1 already depends on.

```bash
python main.py db-init
```

creates `games_db.sqlite` in the repo root (auto-created on first use of any
command anyway — `db-init` just makes that explicit).

## CLI Commands

```bash
# Interactive game — unchanged from Tier 1
python main.py

# Initialize the local database
python main.py db-init

# Import a chess.com user's game history (public API, no auth/API key needed)
python main.py import-chesscom hikaru
python main.py import-chesscom hikaru --months 3   # only the last 3 archive months

# Export a stored game (local or imported) as a standalone PGN file
python main.py export-game 12

# Detect the opening played in a stored game
python main.py detect-opening 12

# Show weakest openings, ranked by mistake frequency x severity
python main.py analyze-opening-mistakes
python main.py analyze-opening-mistakes --top 10

# Mark an opening in your repertoire
python main.py add-favorite "Ruy Lopez" study
python main.py add-favorite "Italian Game" master
python main.py add-favorite "King's Gambit" avoid

# List your marked repertoire
python main.py show-favorites
python main.py show-favorites --status study

# Export favorite opening lines as PGN (games/repertoire_<status>.pgn)
python main.py export-repertoire
python main.py export-repertoire --status master
```

Every game you finish playing interactively (`python main.py`) is
auto-saved: a row in `games_db.sqlite` plus a PGN under `games/`. This is
best-effort — a save failure is logged as a warning and never interrupts the
post-game summary you're looking at.

Opening-mistake logging (the `mistakes` table `analyze-opening-mistakes`
reads from) is populated by `OpeningMistakeTracker.analyze_game(game_id, db,
engine=...)` — pass a live `ChessEngine` for real severity judgement. This
isn't wired to a CLI command yet (it requires an engine instance, i.e. a
Stockfish process, per call) — see `openingtracker.py` to script it, e.g.:

```python
from database import GameDatabase
from openingbook import OpeningBook
from openingtracker import OpeningMistakeTracker
from engine import ChessEngine

db = GameDatabase()
tracker = OpeningMistakeTracker(OpeningBook())
engine = ChessEngine(skill_level=20, depth=18)
for game in db.list_games():
    tracker.analyze_game(game["id"], db, engine=engine)
```

## Database Schema

SQLite, `games_db.sqlite`, created/upgraded automatically by
`GameDatabase.init_schema()`:

```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,              -- 'local' | 'chesscom' | 'manual_import'
    chesscom_url TEXT UNIQUE,          -- dedup key for chess.com imports; NULL for local games
    white TEXT, black TEXT, result TEXT,
    date TEXT, time_control TEXT,
    eco TEXT, opening_name TEXT,
    pgn TEXT NOT NULL,
    final_fen TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    move_san TEXT, move_uci TEXT,
    fen_before TEXT, fen_after TEXT,
    eval_cp INTEGER, eval_mate INTEGER,
    classification TEXT,               -- Book|Brilliant|Excellent|Good|Inaccuracy|Mistake|Blunder|MissedWin
    is_book INTEGER DEFAULT 0
);

CREATE TABLE openings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eco TEXT, name TEXT UNIQUE,
    favorite_status TEXT,              -- 'study' | 'master' | 'avoid' | NULL
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    move_id INTEGER REFERENCES moves(id),
    eco TEXT, ply INTEGER,
    severity TEXT,                     -- 'Minor' | 'LostAdvantage' | 'Critical'
    eval_before INTEGER, eval_after INTEGER,
    played_move TEXT, book_move TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

`wins`/`losses`/`draws` on `openings` are tracked from White's (Agent 17's)
perspective for locally-played games (the intended use case — tracking your
own repertoire). `upsert_opening_result()` is generic and could be called
per-imported-chess.com-game too if you want repertoire stats blended with
imported history; that step isn't done automatically today.

## Move Classification

`moveanalyzer.py`'s `MoveAnalyzer.classify_move()` compares the played move
against the engine's top candidate moves and buckets it by **centipawn loss**
(how much worse the resulting position is than the best available move, from
the mover's perspective):

| Label | Condition |
|---|---|
| `Book` | Move matches a known line in the ECO opening dataset |
| `Brilliant` | The engine's best move, recovering >=300cp from a bad/equal prior position *(requires `eval_before_move`, an external static eval of the position before any candidate move — without it, Brilliant is never assigned)* |
| `Excellent` | cp_loss <= 20 |
| `Good` | cp_loss <= 50 |
| `Inaccuracy` | cp_loss <= 150 |
| `Mistake` | cp_loss <= 300 |
| `Blunder` | cp_loss > 300 |
| `MissedWin` | Position was winning (best move keeps eval >= +200) and the played move drops below +100, regardless of raw cp_loss |

Thresholds are module-level constants at the top of `moveanalyzer.py` —
tune them there. They were chosen to be reasonable, transparent buckets, not
fit against a labeled dataset (there isn't one — the classifier's input *is*
Stockfish's own evaluation, so there's no independent ground truth to score
"accuracy" against). Correctness is covered by deterministic threshold tests
in `test_tier1_5.py` instead — see `test_classify_*`.

If the played move isn't among the engine's top-N candidates at all, it's
conservatively treated as at least as bad as the worst of the N candidates
evaluated (a slight underestimate of how bad it might actually be, since the
engine wasn't asked to score it directly).

## Opening Detection & Deviation Tracking

`openingbook.py` bundles
[lichess-org/chess-openings](https://github.com/lichess-org/chess-openings)
(`resources/openings/eco_a.tsv` .. `eco_e.tsv`, ECO volumes A–E, ~3,800
named lines, loaded once into an in-memory move-sequence trie). This
replaces the "polyglot opening book" originally scoped — a polyglot `.bin`
encodes move weights, not names, so it can't answer "what is this opening
called" on its own; this dataset is real, sourced, and does.

- `OpeningBook.detect(san_moves)` — longest-prefix match; returns the most
  specific named line the game's move sequence matches.
- `OpeningBook.is_book_move(san_so_far, next_san)` — still-in-theory check.
- `OpeningMistakeTracker.analyze_game()` finds the first move that leaves
  the book, then (if given a live `ChessEngine`) judges whether that
  deviation actually cost anything:
  - eval swing < 50cp against the mover -> **sound deviation**, not logged
    as a mistake at all (many reasonable moves simply aren't in a ~3,800-line
    dataset — that's not the same as a mistake)
  - 50–150cp -> `Minor`
  - 150cp+, or the position flips from clearly winning to clearly losing
    for the mover -> `Critical` (with a `LostAdvantage` band in between for
    the non-flip case)
- `OpeningMistakeTracker.study_plan()` ranks openings by
  `mistake_count x severity_weight` (Minor=1, LostAdvantage=2, Critical=4).
- `OpeningMistakeTracker.recommend_favorites()` suggests `study` (>=2
  Critical mistakes logged) or `master` (>=5 games, >=70% win rate) — purely
  advisory; nothing is written until you call
  `db.set_favorite_status(...)` yourself (or `add-favorite` on the CLI).

## Module Reference

| Module | Class | Responsibility |
|---|---|---|
| `database.py` | `GameDatabase` | SQLite schema, CRUD, analytics |
| `openingbook.py` | `OpeningBook` | ECO dataset loading, opening detection, book-deviation checks (stateless) |
| `pgnhandler.py` | `PgnExporter` | Board -> `chess.pgn.Game`, headers/annotations, save/auto_save |
| `moveanalyzer.py` | `MoveAnalyzer` | Move classification (8 labels + Book) |
| `chesscom_integration.py` | `ChessComImporter` | chess.com public API client, PGN-file fallback import |
| `openingtracker.py` | `OpeningMistakeTracker` | Deviation detection, severity, study plan, favorite suggestions |

## Fixes made to existing Tier 1 files (in scope, confirmed with the user)

- **`engine.py`**: `get_best_move_with_evaluation()` previously always
  returned `{"eval": 0}` — a stub. It now returns a real evaluation
  (`{"eval": cp, "mate": moves_to_mate}`) from Stockfish. This also fixed a
  live crash: `main.py` already read `eval_info['mate']`, a key that never
  existed on the old stub, so JARVIS's first move in a real interactive game
  would raise `KeyError`. Added `get_top_moves_with_eval()` (new method,
  used by move classification).
- **`main.py`**: added the 8 subcommands above (bare `python main.py` is
  unaffected — it still runs `main()` directly), a best-effort auto-save
  hook at game-end, and UTF-8 stdout/stderr reconfiguration (Windows
  consoles otherwise default to a codepage that can't encode the Unicode
  chess pieces `BoardVisualizer` prints — the same class of bug already
  fixed once in `setup_stockfish.py`, discovered again here while verifying
  the auto-save hook against a real game).

`game.py` and `board.py` were not touched.

## Known issues found but *not* fixed (out of this pass's scope)

- **`game.py.get_game_status()`**: the checkmate "who loses" text has the
  condition inverted (`loser = "Black" if self.board.turn else "White"`) —
  after Black delivers mate (e.g. Fool's Mate, `...Qh4#`), it prints
  "Black loses" when White was actually mated. Doesn't affect any Tier 1.5
  data — `board.result()` (used for PGN/DB `result`) is correct regardless;
  only the printed status line is wrong.
- **`main.py`'s interactive loop**: if stdin hits EOF (e.g. piped input runs
  out, or stdin is closed/non-interactive), `input()` raises `EOFError`,
  which the loop's broad `except Exception` catches and retries
  indefinitely — a tight infinite loop with no backoff. Never triggered by a
  real person typing at a real terminal (stdin doesn't EOF while you're
  there), but worth knowing if you ever script the interactive mode.

## Deferred (spec item 8 — no detail was ever given for these)

Time controls (bullet/blitz/rapid/classical tagging), an Elo display, a
"suggest top 3 moves" command, and save/load game slots. None of these were
specified beyond a name in the original request; left for a follow-up pass
with actual requirements.

## Tests

```bash
python test_tier1.py      # Tier 1 — 8/8
python test_tier1_5.py    # Tier 1.5 — 38/38 (unit + integration)
```

`test_tier1_5.py` follows `test_tier1.py`'s existing lightweight harness (no
pytest dependency). Live chess.com API tests are opt-in — the default run
uses a fixed PGN fixture, not the network; set `RUN_LIVE_NETWORK_TESTS=1` to
also exercise the real API against a known public account.
