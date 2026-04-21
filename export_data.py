"""Export timeline data from Neon PostgreSQL to a local JSON file.

Run periodically to keep a local backup:
    uv run python export_data.py

Requires DATABASE_URL environment variable (or .env file).
"""

import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "timeline.json")


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

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(rows, f, indent=2)

    print(f"Exported {len(rows)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    export()
