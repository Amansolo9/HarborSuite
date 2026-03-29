from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def run(command: list[str], cwd: Path) -> None:
    if command and command[0] == "npm":
        result = subprocess.run(" ".join(command), cwd=str(cwd), check=False, shell=True)
    else:
        result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" not in database_url:
        raise SystemExit(
            "verify_non_docker.py requires PostgreSQL. Set DATABASE_URL to a postgresql+psycopg URL before running."
        )

    run([sys.executable, "-m", "pytest", "unit_tests", "API_tests"], ROOT)
    run(["npm", "install"], FRONTEND)
    run(["npm", "run", "test"], FRONTEND)
    run(["npm", "run", "build"], FRONTEND)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
