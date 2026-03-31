# HarborSuite Offline Hotel Commerce & PMS

This folder is the full product workspace (`fullstack/`).

## One-command Docker start (offline runtime profile)

From this directory, run:

```bash
docker compose up
```

If you need to build images first in a connected environment:

```bash
docker compose build
```

The services will be available at:

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:5173`

Docker compose starts all services:

- `db`: PostgreSQL 16 (`localhost:5432`)
- `app`: FastAPI backend (`localhost:8000`)
- `frontend`: prebuilt Vite preview server (`localhost:5173`)

Docker startup does not run `npm install` at container runtime; frontend dependencies are baked into the image during build.

Production-safe compose profile:

```bash
docker compose -f docker-compose.prod.yml up
```

The production profile requires strong secrets, sets `APP_ENV=production`, enables secure cookies, and disables demo seeding.

## Local development

### Backend

PostgreSQL must be running locally before non-Docker backend startup/tests. Quick local bootstrap:

```bash
docker compose up -d db
```

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
# Windows PowerShell
$env:DATABASE_URL="postgresql+psycopg://harborsuite:harborsuite@localhost:5432/harborsuite"
# Linux/macOS
export DATABASE_URL="postgresql+psycopg://harborsuite:harborsuite@localhost:5432/harborsuite"
python scripts/bootstrap_db.py
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Local backend defaults to PostgreSQL (`postgresql+psycopg://harborsuite:harborsuite@localhost:5432/harborsuite`).

If you want a quick SQLite-only fallback for ad hoc local development:

```bash
# Windows PowerShell
$env:DATABASE_URL="sqlite:///./fullstack.db"
# Linux/macOS
export DATABASE_URL="sqlite:///./fullstack.db"
python scripts/bootstrap_db.py
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev URL: `http://localhost:5173`

Frontend tests:

```bash
cd frontend
npm install
npm run test
```

Frontend browser E2E (Playwright):

```bash
cd frontend
npm install
npx playwright install
npm run test:e2e
```

Notes:

- Browser auth uses httpOnly cookie sessions by default (token is not stored in browser Web Storage).
- For local non-HTTPS dev, `SESSION_COOKIE_SECURE=false` default applies in `APP_ENV=dev`.
- E2E runner bootstraps schema + seed automatically via `python scripts/bootstrap_db.py` before backend startup.

Minimal acceptance check:

```bash
python -m pytest unit_tests API_tests
cd frontend
npm install
npm run test
npm run build
npx playwright install
npm run test:e2e
```

## Tests

```bash
python -m pytest unit_tests API_tests
```

Non-Docker verification (backend + frontend):

```bash
python scripts/verify_non_docker.py
```

`verify_non_docker.py` enforces a PostgreSQL `DATABASE_URL` by default so local acceptance verification matches deployment requirements.

PostgreSQL smoke target (when `DATABASE_URL` points to PostgreSQL):

```bash
python -m pytest API_tests/test_postgres_smoke.py
```

Or:

```bash
./run_tests.sh
```

## Development seed credentials

Demo credentials are only seeded when `SEED_DEMO_DATA=true` (default in dev). In non-dev environments, startup blocks if demo seeding is enabled.

- Demo role usernames are listed in the login panel.
- Demo password (dev only): `Harbor#2026!`

## Security runtime guard

- Set `APP_ENV=production` (or non-dev value) outside local development.
- In non-dev mode you must provide strong secrets for `JWT_SECRET` and `EXPORT_CHECKSUM_SECRET`.
- Startup refuses to run with known demo secrets or `SEED_DEMO_DATA=true`.

## Local printer adapter

- Print jobs are always written to `data/print_queue/<organization>/print-job-<id>.json` for audit/fallback.
- To enable direct local dispatch, set `PRINT_COMMAND_TEMPLATE` with `{file}` placeholder.
  - Example (Windows PowerShell print verb): `PRINT_COMMAND_TEMPLATE=powershell -Command Start-Process -FilePath "{file}" -Verb Print`

## Core API coverage in this build

- Auth + session: `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Hotel overview: `GET /api/v1/operations/overview`
- Orders: create/list/transition
- Order dimensions: split/merge/list allocations by supplier/warehouse/SLA
- Folios: list/charge/payment/adjustment/reversal/split/merge/receipt/print
- Content governance: create/list/approve/rollback
- Complaints + evidence packet export + 7-day policy window
- Mutual guest/staff ratings
- Offline exports + audit logs
- Governance metadata APIs: metrics, lineage, dataset versions, dictionary export
- Acceptance support: credit score, night audit, day-close, GM analytics

## Persistence notes

- Runtime persistence is SQLAlchemy-backed (session tokens, orders, folios, content, complaints, exports, audit events).
- Docker path uses PostgreSQL for persistent on-prem style deployment.
- Non-Docker acceptance verification is PostgreSQL-first.
- SQLite remains an explicit local fallback only when `DATABASE_URL=sqlite:///./fullstack.db` is set.

## Order catalog configuration

- Authoritative order catalog data is read at runtime from `data/order_catalog.json` (or `ORDER_CATALOG_PATH` if set).
- Backend quote/order validation and frontend catalog picker both use this API-backed catalog (`GET /api/v1/orders/catalog`).
- Updating the catalog file does not require frontend code edits.

Architecture and API behavior docs are maintained at repository root (`../docs/design.md`, `../docs/api-spec.md`).
