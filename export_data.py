"""Export timeline data from Neon PostgreSQL to a local JSON file.

Run periodically to keep a local backup:
    uv run python export_data.py

Requires DATABASE_URL environment variable (or .env file).
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
OUTPUT_FILE = Path(__file__).parent / "data" / "timeline.json"


def export():
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT date, bodyweight, added_weight, reps FROM timeline ORDER BY date")
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2))

    print(f"Exported {len(rows)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    export()
