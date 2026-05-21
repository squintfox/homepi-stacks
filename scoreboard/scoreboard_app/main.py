from __future__ import annotations

import os
import sqlite3
from dataclasses import asdict, dataclass
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request


@dataclass
class Player:
    id: int
    name: str
    score: int
    turn_order: int


class AddPlayerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class UpdateScoreRequest(BaseModel):
    score: int


class SortModeRequest(BaseModel):
    sort_mode: str


class ScoreboardState:
    def __init__(self, db_path: str) -> None:
        self._lock = Lock()
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    score INTEGER NOT NULL,
                    turn_order INTEGER NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """)
            conn.execute("""
                INSERT INTO app_state(key, value)
                VALUES('sort_mode', 'turn')
                ON CONFLICT(key) DO NOTHING
                """)
            conn.commit()

    def _get_sort_mode(self, conn: sqlite3.Connection) -> str:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = 'sort_mode'"
        ).fetchone()
        return row[0] if row is not None else "turn"

    def _fetch_players(self, conn: sqlite3.Connection, sort_mode: str) -> list[dict]:
        order_by = (
            "score DESC, turn_order ASC" if sort_mode == "score" else "turn_order ASC"
        )
        rows = conn.execute(
            f"SELECT id, name, score, turn_order FROM players ORDER BY {order_by}"
        ).fetchall()

        return [
            asdict(Player(id=row[0], name=row[1], score=row[2], turn_order=row[3]))
            for row in rows
        ]

    def snapshot(self) -> dict:
        with self._lock:
            with self._connect() as conn:
                sort_mode = self._get_sort_mode(conn)
                players = self._fetch_players(conn, sort_mode)

        return {
            "players": players,
            "sort_mode": sort_mode,
        }

    def add_player(self, name: str) -> dict:
        clean_name = " ".join(name.split()).strip()
        if not clean_name:
            raise ValueError("Player name cannot be empty.")

        with self._lock:
            with self._connect() as conn:
                # Enforce case-insensitive uniqueness for player names.
                existing = conn.execute(
                    "SELECT 1 FROM players WHERE lower(name) = lower(?)",
                    (clean_name,),
                ).fetchone()
                if existing is not None:
                    raise ValueError("Player name already exists.")

                next_turn = conn.execute(
                    "SELECT COALESCE(MAX(turn_order), 0) + 1 FROM players"
                ).fetchone()[0]

                conn.execute(
                    "INSERT INTO players(name, score, turn_order) VALUES (?, 0, ?)",
                    (clean_name, next_turn),
                )
                conn.commit()

        return self.snapshot()

    def update_score(self, player_id: int, score: int) -> dict:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE players SET score = ? WHERE id = ?",
                    (score, player_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError("Player not found.")
                conn.commit()

        return self.snapshot()

    def reset_scores(self) -> dict:
        with self._lock:
            with self._connect() as conn:
                conn.execute("UPDATE players SET score = 0")
                conn.commit()

        return self.snapshot()

    def set_sort_mode(self, sort_mode: str) -> dict:
        if sort_mode not in {"turn", "score"}:
            raise ValueError("Invalid sort mode.")

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO app_state(key, value)
                    VALUES('sort_mode', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (sort_mode,),
                )
                conn.commit()

        return self.snapshot()


app = FastAPI(title="Scoreboard")
templates = Jinja2Templates(directory="scoreboard_app/templates")
state = ScoreboardState(
    db_path=os.getenv("SCOREBOARD_DB_PATH", "/app/data/scoreboard.db")
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"title": "Scoreboard"})


@app.get("/api/state")
async def get_state() -> dict:
    return state.snapshot()


@app.post("/api/players")
async def add_player(payload: AddPlayerRequest) -> dict:
    try:
        return state.add_player(payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/players/{player_id}/score")
async def update_score(player_id: int, payload: UpdateScoreRequest) -> dict:
    try:
        return state.update_score(player_id, payload.score)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/reset")
async def reset_scores() -> dict:
    return state.reset_scores()


@app.put("/api/sort-mode")
async def set_sort_mode(payload: SortModeRequest) -> dict:
    try:
        return state.set_sort_mode(payload.sort_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
