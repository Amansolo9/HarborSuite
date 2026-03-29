from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.database import SessionLocal, initialize_database
from backend.services.seed import seed_if_empty


def main() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_if_empty(db)


if __name__ == "__main__":
    main()
