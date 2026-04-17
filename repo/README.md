# HarborSuite Offline Hotel Commerce & PMS

This folder is the full product workspace (`fullstack/`). Everything below runs inside Docker - no local Python, Node, or Playwright installs are required for reviewers.

## Quick start (Docker-only, strict)

From this directory:

```bash
docker compose up --build
```

That single command starts the full stack. All dependencies (Python packages, Node modules, Playwright browsers) are baked into the images at build time - nothing is installed into your host environment at runtime.

Services are available at:

| Service  | URL                       | Container        |
|----------|---------------------------|------------------|
| Backend  | `http://localhost:8000`   | `app`            |
| Frontend | `http://localhost:5173`   | `frontend`       |
| Database | `localhost:5432`          | `db` (PostgreSQL 16) |

To shut down:

```bash
docker compose down
```

Production-safe compose profile (requires strong secrets, disables demo seeding):

```bash
docker compose -f docker-compose.prod.yml up
```

## Demo credentials (dev profile only)

Demo data is seeded when `SEED_DEMO_DATA=true` (the default in the `dev` profile). Every seeded user shares the same password.

| Role              | Username                     | Password        |
|-------------------|------------------------------|-----------------|
| Guest             | `guest@seabreeze.local`      | `Harbor#2026!`  |
| Front Desk        | `desk@seabreeze.local`       | `Harbor#2026!`  |
| Service Staff     | `service@seabreeze.local`    | `Harbor#2026!`  |
| Finance           | `finance@seabreeze.local`    | `Harbor#2026!`  |
| Content Editor    | `editor@seabreeze.local`     | `Harbor#2026!`  |
| General Manager   | `gm@seabreeze.local`         | `Harbor#2026!`  |
| Cross-org GM      | `gm@summit.local`            | `Harbor#2026!`  |

In `APP_ENV=production` the startup guard refuses to boot with demo seeding enabled or with the demo `JWT_SECRET` / `EXPORT_CHECKSUM_SECRET` values still in place.

## Verification (copy-paste acceptance flow)

After `docker compose up --build` reports both `app` and `frontend` as ready, run these checks from any host shell. Every step lists the expected outcome so a reviewer can confirm acceptance without reading source.

### 1. Backend health

```bash
curl -s http://localhost:8000/health
```

Expected body:

```json
{"status":"ok","mode":"offline-ready"}
```

### 2. Login and issue a bearer token

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -H 'x-harborsuite-auth-mode: bearer' \
  -d '{"username":"gm@seabreeze.local","password":"Harbor#2026!"}'
```

Expected: HTTP 200 with a JSON body containing `access_token`, `role: "general_manager"`, and `organization_name: "Seabreeze Harbor"`. Copy the `access_token` value for the next step.

### 3. Call an authenticated endpoint

```bash
curl -s http://localhost:8000/api/v1/operations/overview \
  -H "Authorization: Bearer <paste access_token here>"
```

Expected: HTTP 200 JSON body with `property_name`, `role`, and non-negative counters such as `open_folios`, `active_orders`, `open_complaints`, `pending_exports`.

### 4. Reject unauthenticated access

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/orders
```

Expected output: `401`.

### 5. Frontend UI acceptance walk-through

Open `http://localhost:5173` in a browser and:

1. Log in as `gm@seabreeze.local` / `Harbor#2026!` - you should land on the GM dashboard and see folio, order, and complaint summaries.
2. Log out, then log in as `desk@seabreeze.local` - confirm the Folio Operations panel appears with the seeded Maya Chen folio.
3. Log out, then log in as `guest@seabreeze.local` - confirm only the guest's own folio and order composer are visible; back-office panels are hidden.

If all five checks match, the deployment is accepted.

## Automated test run (Docker-only)

All tests also run inside the `app` image with no host-side dependency installs:

```bash
docker compose build app
docker compose run --rm app sh -c \
  "DATABASE_URL=sqlite:///./migration_check.db python -m alembic upgrade head && \
   DATABASE_URL=sqlite:///./migration_check.db python -m pytest unit_tests API_tests"
```

Expected: pytest summary ends with `passed` for every collected test.

The helper `./run_tests.sh` wraps the same flow. If you invoke it on a host that already has pytest available it will use that; otherwise it falls back to the Docker path above.

## Core API coverage in this build

- Auth + session: `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`
- Hotel overview: `GET /api/v1/operations/overview`
- Orders: quote / create / list / transition / split / merge / allocations
- Folios: list / charge / payment / adjustment / reversal / split / merge / receipt / invoice / print
- Content governance: create / list / approve / rollback
- Complaints + 7-day evidence packet export (metadata + downloadable file)
- Mutual guest/staff ratings with 7-day window
- Offline exports + tamper-evident audit logs
- Governance metadata APIs: metrics, lineage, dataset versions, dictionary export
- Acceptance support: credit score, night audit, day-close, GM analytics

## Security runtime guard

- `APP_ENV=production` must be set outside dev.
- Strong `JWT_SECRET` and `EXPORT_CHECKSUM_SECRET` are mandatory outside dev; startup refuses to run with known demo secrets or `SEED_DEMO_DATA=true`.
- Browser auth uses httpOnly cookie sessions by default; access tokens are not stored in browser Web Storage.
- CSRF double-submit protection is enforced on mutating cookie-authenticated requests.

## Local printer adapter

- Print jobs are always written to `data/print_queue/<organization>/print-job-<id>.json` for audit/fallback.
- To enable direct local dispatch, set `PRINT_COMMAND_TEMPLATE` with a `{file}` placeholder; the backend invokes the command via `subprocess` with argv parameterization, not a shell.
  - Windows example: `PRINT_COMMAND_TEMPLATE=powershell -Command Start-Process -FilePath "{file}" -Verb Print`

## Order catalog configuration

- Authoritative order catalog data is read at runtime from `data/order_catalog.json` (or `ORDER_CATALOG_PATH` if set).
- Backend quote/order validation and the frontend catalog picker both use `GET /api/v1/orders/catalog`; updating the catalog file does not require frontend code changes.

## Persistence notes

- Runtime persistence is SQLAlchemy-backed (session tokens, orders, folios, content, complaints, exports, audit events).
- The Docker profile uses PostgreSQL for persistent on-prem-style deployment.
- SQLite is only used by the in-container test target (`sqlite:///./migration_check.db`) and is not a deployment target.

## Reference documentation

Architecture and API behavior documentation lives at the repository root: `../docs/design.md` and `../docs/api-spec.md`.
