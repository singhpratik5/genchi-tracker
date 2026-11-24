import os
import sqlite3
from datetime import datetime, timezone

STAGES = ["enquiry", "qualified", "booked", "completed", "paid"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    country TEXT,
    source TEXT NOT NULL DEFAULT 'direct',
    use_case TEXT NOT NULL,
    details TEXT,
    stage TEXT NOT NULL DEFAULT 'enquiry'
);
CREATE TABLE IF NOT EXISTS stage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES requests(id),
    stage TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_request ON stage_events(request_id);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(os.environ.get("GENCHI_DB", "genchi.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
    finally:
        conn.close()
