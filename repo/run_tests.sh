#!/usr/bin/env sh
set -eu

if python -m pytest --version >/dev/null 2>&1; then
  DATABASE_URL=sqlite:///./migration_check.db python -m alembic upgrade head
  python -m pytest unit_tests API_tests
else
  docker compose build app
  docker compose run --rm app sh -c "DATABASE_URL=sqlite:///./migration_check.db python -m alembic upgrade head && python -m pytest unit_tests API_tests"
fi
