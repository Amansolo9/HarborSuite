from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/expire_sessions.py <sqlite-db-path>")
    db_path = Path(sys.argv[1]).resolve()
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("update session_tokens set last_seen_at='2000-01-01T00:00:00+00:00'")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
