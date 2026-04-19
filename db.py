"""Database helpers for timeline storage (PostgreSQL via psycopg2)."""

import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

# Local JSON fallback path (used when DATABASE_URL is not set)
_LOCAL_FILE = Path(__file__).parent / "data" / "timeline.json"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS timeline (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL,
    bodyweight REAL NOT NULL,
    added_weight REAL NOT NULL,
    reps INTEGER NOT NULL
);
"""


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create the timeline table if it doesn't exist."""
    if not DATABASE_URL:
        return
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
        conn.commit()


# ---------------------------------------------------------------------------
# CRUD — Postgres
# ---------------------------------------------------------------------------

def _pg_load() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, date, bodyweight, added_weight, reps FROM timeline ORDER BY date")
            return [dict(row) for row in cur.fetchall()]


def _pg_add(entry: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO timeline (date, bodyweight, added_weight, reps) VALUES (%s, %s, %s, %s)",
                (entry["date"], entry["bodyweight"], entry["added_weight"], entry["reps"]),
            )
        conn.commit()


def _pg_delete(row_id: int) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM timeline WHERE id = %s", (row_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# CRUD — local JSON fallback
# ---------------------------------------------------------------------------

def _local_load() -> list[dict]:
    if _LOCAL_FILE.exists():
        return json.loads(_LOCAL_FILE.read_text())
    return []


def _local_add(entry: dict) -> None:
    entries = _local_load()
    entries.append(entry)
    _LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_FILE.write_text(json.dumps(entries, indent=2))


def _local_delete(index: int) -> None:
    entries = _local_load()
    entries.pop(index)
    _LOCAL_FILE.write_text(json.dumps(entries, indent=2))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_timeline() -> list[dict]:
    return _pg_load() if DATABASE_URL else _local_load()


def add_timeline_entry(entry: dict) -> None:
    if DATABASE_URL:
        _pg_add(entry)
    else:
        _local_add(entry)


def delete_timeline_entry(identifier: int) -> None:
    """Delete by row id (Postgres) or list index (local JSON)."""
    if DATABASE_URL:
        _pg_delete(identifier)
    else:
        _local_delete(identifier)
