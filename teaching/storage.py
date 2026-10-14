"""SQLite storage for sessions, messages and events.

Messages are only ever added, never changed, so every conversation can be
reviewed later. Events record the teaching decisions (the level chosen, each
re-explanation), and llm_calls records every provider call so real usage
can be measured once a paid API is connected.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    concept TEXT NOT NULL,
    stage TEXT NOT NULL,              -- assess | discuss | check | complete
    level TEXT,                       -- beginner | some_experience
    level_reason TEXT,
    gaps TEXT NOT NULL DEFAULT '[]',
    questions_asked INTEGER NOT NULL DEFAULT 0,
    reexplains INTEGER NOT NULL DEFAULT 0,
    checks_asked INTEGER NOT NULL DEFAULT 0,
    checks_correct INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,               -- learner | tutor | app
    content TEXT NOT NULL,
    task TEXT,                        -- which teaching step produced it
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    provider TEXT NOT NULL,
    task TEXT NOT NULL,
    ok INTEGER NOT NULL,
    error TEXT,
    duration_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

-- A repeated request id returns the first answer instead of running twice.
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columns added after the first version. Older databases get them on start-up.
ADDED_COLUMNS = {
    "sessions": {
        "checks_asked": "INTEGER NOT NULL DEFAULT 0",
        "checks_correct": "INTEGER NOT NULL DEFAULT 0",
    },
}


def init(path: str) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        for table, columns in ADDED_COLUMNS.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    finally:
        conn.close()


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value, default=None):
    return json.loads(value) if value else default
