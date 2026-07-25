import io
import json
import logging
import os
import tempfile
import urllib.error
import urllib.request
import uuid
from typing import Optional

import chess.pgn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from game_engine import GameEngine
from openingbook import OpeningBook
from database import GameDatabase
from chesscom_integration import ChessComImporter, USER_AGENT

logger = logging.getLogger(__name__)

app = FastAPI(title="JARVIS Chess API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    uci: str


class FavoriteRequest(BaseModel):
    status: str  # study | master | avoid


class PuzzleResultRequest(BaseModel):
    puzzle_id: str
    correct: bool


# ---------------------------------------------------------------------------
# GameManager — in-memory registry of active games + their WebSocket
# connections. No persistence across a server restart; finished games are
# already persisted via GameEngine.save_and_export(), same as the CLI.
# ---------------------------------------------------------------------------

class GameManager:
    def __init__(self):
        self.games: dict = {}         # game_id -> GameEngine
        self.connections: dict = {}   # game_id -> set[WebSocket]
        # Loaded once (~3,800 ECO lines) and shared by every GameEngine this
        # manager creates — see game_engine.py's constructor docstring.
        self.opening_book = OpeningBook()

    def create_game(self, skill_level: int = 20, depth: int = 10) -> GameEngine:
        game_id = f"game_{uuid.uuid4().hex[:12]}"
        game = GameEngine(skill_level=skill_level, depth=depth, opening_book=self.opening_book)
        game.game_id = game_id
        self.games[game_id] = game
        self.connections[game_id] = set()
        return game

    def get_game(self, game_id: str) -> Optional[GameEngine]:
        return self.games.get(game_id)

    def close_game(self, game_id: str):
        self.games.pop(game_id, None)
        self.connections.pop(game_id, None)

    def get_all_games(self) -> dict:
        return self.games


manager = GameManager()


@app.get("/")
def root():
    return {"service": "JARVIS Chess API", "status": "ok", "active_games": len(manager.games)}


# ---------------------------------------------------------------------------
# /api/games/*
# ---------------------------------------------------------------------------

@app.post("/api/games/new")
def create_game(skill_level: int = 20, depth: int = 10):
    game = manager.create_game(skill_level=skill_level, depth=depth)
    return {"game_id": game.game_id, "state": game.get_state()}


@app.get("/api/games")
def list_games():
    return {
        "games": [
            {
                "game_id": gid,
                "turn": g.get_state()["turn"],
                "status": g.get_status(),
                "moves": len(g.get_moves()),
            }
            for gid, g in manager.get_all_games().items()
        ]
    }


@app.get("/api/games/{game_id}/state")
def get_game_state(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"No game with id {game_id}")
    return game.get_state()


@app.post("/api/games/{game_id}/move")
def make_move(game_id: str, req: MoveRequest):
    """
    Applies the player's move, then — same as the WebSocket flow — auto-plays
    JARVIS's reply if the player's move didn't already end the game. Kept
    behaviorally identical to the WebSocket path for REST clients/testing.
    """
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"No game with id {game_id}")

    success, message = game.move(req.uci)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    if not game.is_game_over():
        jarvis_uci, _ = game.get_best_move()
        if jarvis_uci:
            game.move(jarvis_uci)

    if game.is_game_over():
        try:
            game.save_and_export()
        except Exception as e:
            logger.warning(f"Auto-save failed for {game_id}: {e}")

    return game.get_state()


@app.get("/api/games/{game_id}/moves")
def get_game_moves(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"No game with id {game_id}")
    return {"moves": game.get_moves()}


@app.post("/api/games/{game_id}/end")
def end_game(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"No game with id {game_id}")
    db_game_id, path = game.save_and_export()
    manager.close_game(game_id)
    return {"saved_game_id": db_game_id, "pgn_path": path}


@app.get("/api/games/{game_id}/engine-stats")
def engine_stats(game_id: str):
    """Move-timing stats for JARVIS's own get_best_move() calls in this
    (live, in-memory) game — see GameEngine.get_engine_stats()."""
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"No game with id {game_id}")
    return game.get_engine_stats()


# ---------------------------------------------------------------------------
# /api/games/history/* — stored games (DB), for replay/analysis. Distinct
# from /api/games/{game_id}/* above, which only ever addresses a *live*
# in-memory GameManager game (string id) — these take the DB's integer id.
# ---------------------------------------------------------------------------

@app.get("/api/games/history")
def games_history(source: Optional[str] = None):
    db = GameDatabase()
    try:
        games = db.list_games(source=source)
    finally:
        db.close()
    return {
        "games": [
            {
                "id": g["id"],
                "source": g["source"],
                "white": g["white"],
                "black": g["black"],
                "result": g["result"],
                "date": g["date"],
                "eco": g["eco"],
                "opening_name": g["opening_name"],
            }
            for g in games
        ]
    }


@app.get("/api/games/history/{game_id}/replay")
def games_history_replay(game_id: int):
    db = GameDatabase()
    try:
        game = db.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail=f"No stored game with id {game_id}")
        move_rows = db.get_moves(game_id)
    finally:
        db.close()

    # `moves.fen_after` is never actually populated (game_engine.py's
    # save_and_export() doesn't pass it to save_moves(), and chess.com/manual
    # imports never call save_moves() at all — see ChessComImporter). The PGN
    # itself is always present, though, so reconstruct FEN from that for
    # every game, and merge in eval/classification by ply where it exists.
    analysis_by_ply = {
        m["ply"]: {
            "eval": (m["eval_cp"] / 100.0) if m["eval_cp"] is not None else None,
            "eval_mate": m["eval_mate"],
            "classification": m["classification"],
        }
        for m in move_rows
    }

    moves = []
    parsed = chess.pgn.read_game(io.StringIO(game["pgn"]))
    if parsed is not None:
        board = parsed.board()
        for i, node in enumerate(parsed.mainline(), start=1):
            san = board.san(node.move)
            uci = node.move.uci()
            board.push(node.move)
            extra = analysis_by_ply.get(i, {"eval": None, "eval_mate": None, "classification": None})
            moves.append({"ply": i, "san": san, "uci": uci, "fen": board.fen(), **extra})

    return {
        "id": game["id"],
        "source": game["source"],
        "white": game["white"],
        "black": game["black"],
        "result": game["result"],
        "date": game["date"],
        "eco": game["eco"],
        "opening_name": game["opening_name"],
        "analyzed": bool(move_rows),
        "moves": moves,
    }


# ---------------------------------------------------------------------------
# /api/openings/*
# ---------------------------------------------------------------------------

@app.get("/api/openings/stats")
def openings_stats():
    db = GameDatabase()
    try:
        analytics = db.get_analytics()
        openings = db.list_openings()
        mistake_counts = {}
        for m in db.get_mistakes():
            eco = m.get("eco")
            if eco:
                mistake_counts[eco] = mistake_counts.get(eco, 0) + 1
    finally:
        db.close()

    for opening in openings:
        opening["mistake_count"] = mistake_counts.get(opening.get("eco"), 0)

    return {"analytics": analytics, "openings": openings}


@app.get("/api/openings/{eco}/analysis")
def opening_analysis(eco: str):
    db = GameDatabase()
    try:
        lines = [o for o in db.list_openings() if o.get("eco") == eco]
        mistakes = db.get_mistakes(eco=eco)
    finally:
        db.close()

    total_games = sum(o["games_played"] for o in lines)
    total_wins = sum(o["wins"] for o in lines)
    return {
        "eco": eco,
        "name": manager.opening_book.eco_names.get(eco, eco),
        "lines": lines,
        "total_games": total_games,
        "win_rate": (total_wins / total_games) if total_games else None,
        "mistakes": mistakes,
    }


@app.post("/api/openings/{opening}/favorite")
def set_favorite(opening: str, req: FavoriteRequest):
    if req.status not in ("study", "master", "avoid"):
        raise HTTPException(status_code=400, detail="status must be study, master, or avoid")
    db = GameDatabase()
    try:
        db.set_favorite_status(opening, req.status)
    finally:
        db.close()
    return {"opening": opening, "favorite_status": req.status}


# ---------------------------------------------------------------------------
# /api/import/*
# ---------------------------------------------------------------------------

@app.post("/api/import/chesscom/{username}")
def import_chesscom(username: str, months: Optional[int] = None):
    db = GameDatabase()
    try:
        importer = ChessComImporter()
        summary = importer.import_user(username, db, months=months)
    finally:
        db.close()
    return {
        "imported": summary.imported,
        "skipped": summary.skipped,
        "errors": summary.errors,
        "error_messages": summary.error_messages[:10],
    }


@app.post("/api/import/pgn")
def import_pgn(file: UploadFile = File(...)):
    content = file.file.read()
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pgn", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        db = GameDatabase()
        try:
            importer = ChessComImporter()
            summary = importer.import_pgn_file(tmp_path, db)
        finally:
            db.close()
    finally:
        os.unlink(tmp_path)
    return {
        "imported": summary.imported,
        "errors": summary.errors,
        "error_messages": summary.error_messages[:10],
    }


# ---------------------------------------------------------------------------
# /api/puzzle/* — lichess.org's public puzzle API (no auth required), same
# urllib approach as ChessComImporter above.
# ---------------------------------------------------------------------------

LICHESS_PUZZLE_URL = "https://lichess.org/api/puzzle/next"


def _fetch_lichess_puzzle() -> dict:
    req = urllib.request.Request(LICHESS_PUZZLE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _puzzle_from_lichess(data: dict) -> dict:
    """
    Reshapes lichess's puzzle response into {id, fen, solution_move, rating,
    themes}. lichess puzzles start from a real game position (`game.pgn`, SAN
    moves with no move numbers) after `puzzle.initialPly` half-moves; the
    first entry in `puzzle.solution` (UCI) is the opponent's forced setup
    move, and the position after that is where the player must find the
    single key move — `solution[1]`. (Some lichess puzzles chain further
    forced replies beyond that; this only checks the first key move, not the
    full continuation.)
    """
    puzzle, game = data["puzzle"], data["game"]
    solution = puzzle["solution"]

    board = chess.Board()
    # initialPly is 0-indexed (the ply *index* of the last move already
    # played), so the slice needs +1 to include it.
    for san in game["pgn"].split()[: puzzle["initialPly"] + 1]:
        board.push_san(san)
    board.push(chess.Move.from_uci(solution[0]))

    return {
        "id": puzzle["id"],
        "fen": board.fen(),
        "solution_move": solution[1] if len(solution) > 1 else None,
        "rating": puzzle["rating"],
        "themes": puzzle.get("themes", []),
    }


@app.get("/api/puzzle/random")
def get_random_puzzle():
    try:
        data = _fetch_lichess_puzzle()
        return _puzzle_from_lichess(data)
    except (urllib.error.URLError, KeyError, ValueError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch puzzle from lichess.org: {e}")


@app.post("/api/puzzle/solved")
def record_puzzle_solved(req: PuzzleResultRequest):
    db = GameDatabase()
    try:
        db.record_puzzle_result(req.puzzle_id, req.correct)
    finally:
        db.close()
    return {"status": "recorded"}


@app.get("/api/puzzle/stats")
def puzzle_stats():
    db = GameDatabase()
    try:
        stats = db.get_puzzle_stats()
    finally:
        db.close()
    return stats


# ---------------------------------------------------------------------------
# WebSocket /ws/game/{game_id}
# ---------------------------------------------------------------------------

async def _broadcast(game_id: str, state: dict):
    dead = []
    for ws in manager.connections.get(game_id, set()):
        try:
            await ws.send_json(state)
        except Exception:
            dead.append(ws)
    for ws in dead:
        manager.connections[game_id].discard(ws)


@app.websocket("/ws/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()

    game = manager.get_game(game_id)
    if not game:
        await websocket.send_json({"error": f"No game with id {game_id}"})
        await websocket.close()
        return

    manager.connections[game_id].add(websocket)
    try:
        await websocket.send_json(game.get_state())

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "move":
                uci = data.get("uci", "")
                # Real Stockfish/DB calls are blocking — offload to a thread so
                # the event loop stays free for other connections/games.
                success, message = await run_in_threadpool(game.move, uci)
                if not success:
                    await websocket.send_json({"error": message, "state": game.get_state()})
                    continue

                # Fixes a real bug in the original design sketch: don't auto-play
                # a JARVIS reply if the player's move already ended the game.
                if not game.is_game_over():
                    jarvis_uci, _ = await run_in_threadpool(game.get_best_move)
                    if jarvis_uci:
                        await run_in_threadpool(game.move, jarvis_uci)

                state = game.get_state()
                if game.is_game_over():
                    try:
                        db_game_id, path = await run_in_threadpool(game.save_and_export)
                        state["saved"] = {"game_id": db_game_id, "pgn_path": path}
                    except Exception as e:
                        logger.warning(f"Auto-save failed for {game_id}: {e}")

                await _broadcast(game_id, state)

            elif action == "undo":
                # Mirrors tier1_cli.py's undo semantics: unwind JARVIS's reply
                # and the player's own last move together, if both exist.
                success, _ = await run_in_threadpool(game.undo)
                if success and len(game.get_moves()) > 0:
                    await run_in_threadpool(game.undo)
                await _broadcast(game_id, game.get_state())

            elif action == "set_depth":
                depth = data.get("depth")
                if not isinstance(depth, int) or not (1 <= depth <= 20):
                    await websocket.send_json({"error": "depth must be an integer 1-20"})
                else:
                    await run_in_threadpool(game.set_depth, depth)
                    # Config change, not a board update — ack the requester only,
                    # unlike move/undo which broadcast new game state to everyone.
                    await websocket.send_json({"depth_set": depth})

            else:
                await websocket.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.connections.get(game_id, set()).discard(websocket)
