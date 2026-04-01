# HarborSuite Architecture Foundation

## 1) System scope

HarborSuite is an offline-capable hotel commerce and PMS platform for on-property use. The implementation in `fullstack/` is organized as a Vue frontend and FastAPI backend with SQLAlchemy persistence, role-scoped workflows, auditable operations, governance metadata, day-close controls, and checksum-verified exports.

## 2) Runtime topology

- Frontend (`fullstack/frontend`): Vue + Vite app served from dev server in local and docker workflows.
- Docker frontend image is dependency-prebaked and runs without runtime package fetch (`npm install` is not executed at container start).
- Backend (`fullstack/backend`): FastAPI API with synchronous SQLAlchemy sessions.
- Database:
  - Docker: PostgreSQL service (`db`) consumed by `app`.
  - Local dev/test fallback: SQLite.
- Startup behavior (`backend/app/main.py`):
  - logging setup
  - runtime security guard
  - schema initialization
  - optional seed dataset
  - background scheduler loop for day-close cutoff execution

## 3) Core domain architecture

### 3.1 Identity, security, and sessions

- Users (`UserAccount`) and org isolation (`Organization`) enforce tenant boundaries.
- Sessions use signed bearer tokens plus persisted hashed token records (`SessionToken`).
- Browser clients authenticate through httpOnly session cookie transport (token remains out of Web Storage); bearer token response is retained for non-browser/API-client compatibility.
- Security controls:
  - inactivity timeout (default 15 min)
  - lockout after repeated failures
  - password complexity policy
  - role-based access checks at route dependency layer
- Runtime guard (`backend/core/runtime_guard.py`) blocks non-dev startup when insecure demo secrets or demo seeding are configured.

### 3.2 Orders and quote reconfirmation

Order creation is two-stage by design:

1. `POST /api/v1/orders/confirm-quote` stores a quote snapshot hash (`OrderQuote`) and issues a reconfirm token valid for 10 minutes.
2. `POST /api/v1/orders` requires:
   - reconfirm token
   - quote-consistent payload (items/fees/tax/delivery window)
   - recent confirmation timestamp
   - authoritative catalog unit pricing (client price override rejected)

This enforces price/tax drift protection beyond timestamp freshness. If payload or effective tax rule context differs from the confirmed snapshot, order creation is rejected (`409`).

### 3.3 Multi-spec ordering and delivery windows

- `OrderItemRequest` supports:
  - name, quantity, unit_price
  - `size`
  - freeform `specs` key/value selections
  - `delivery_slot_label`
- Order persistence stores canonicalized item JSON (`order_items_json`) and required delivery window start/end timestamps.
- Delivery window validation ensures chronological correctness and bounded window length.

### 3.4 Service lifecycle and duration metrics

- Orders capture service timing fields:
  - `service_start_at` when transitioning to `in_prep`
  - `service_end_at` when transitioning to terminal service states
- `GET /api/v1/analytics/service-durations` aggregates completed durations by actor role and order type.

### 3.5 Complaints and ratings workflows

- Complaint creation actors are constrained to `guest` and `service_staff` per prompt workflow.
- Complaint submission enforces a 7-day window relative to related folio service activity.
- Complaint packet export is role-scoped (`guest`, `service_staff`, `finance`, `general_manager`) with object-level ownership required for `guest`/`service_staff` reporters.
- Ratings require `order_id` and enforce object-level checks: same organization, completed service state, guest-order participant validation, and eligible staff-role constraints.
- Ratings additionally enforce service-staff order participation via order-level assignment captured during service lifecycle transitions.

### 3.6 Finance controls: night audit and day close

- Night audit (`NightAuditService`) computes per-folio deltas and enforces strict tolerance `abs(delta) <= 0.01`.
- Day-close (`DayCloseRun`) adds:
  - configurable cutoff (default `03:00`)
  - auto-post room and tax charges
  - folio status transitions (`OPEN -> IN_AUDIT -> CLOSED` on pass)
  - persisted run artifacts including failure counts and posting counts
- API route `POST /api/v1/day-close/run` performs on-demand close; scheduled loop executes by cutoff.
- Cross-tenant safeguards:
  - default scope is caller organization
  - multi-organization scope requires explicit super-admin override username allowlist
  - override events are auditable (`night_audit_scope_override`, `day_close_scope_override`)

### 3.7 Governance metadata and lineage

Governance entities provide traceability foundations:

- `MetricDefinition`: metric semantics and source query references
- `DatasetVersion`: versioned dataset schema registry with checksum
- `DataLineage`: metric-to-dataset and source table/query links
- `DataDictionaryField`: exported dictionary fields with sensitivity labels

Routes under `/api/v1/governance/*` provide create/list/export operations for these artifacts.

### 3.8 Export integrity and evidence artifacts

- Export workflow writes concrete payload files and verifies read-back integrity before persisting metadata.
- Checksum derivation uses export payload and configured secret.
- Complaint packets write local PDF + manifest checksum metadata.
- Analytics endpoints are read-only; optional snapshot persistence is triggered through explicit API action and stored as organization-scoped `AnalyticsSnapshot` records.
- Export storage path is anchored to the offline export directory and rejects traversal payloads from user-controlled export type input.

### 3.9 Content targeting and readership lifecycle

- Release visibility requires both:
  - role match (`target_roles`)
  - audience tag match (`target_tags` vs user `audience_tags`, with `all` wildcard)
- Organization targeting gate is also supported (`target_organizations`, with `all` wildcard).
- Approved releases targeted to another organization are visible cross-org when target organization matches the viewer organization id/code.
- First user access to a release creates a read event (`ContentReadEvent`) and increments `readership_count` exactly once per user/release pair.
- Release taxonomy is explicit (`announcement`, `news`, `carousel_promo`) and end-user visibility is approval-gated (`approved` only for non-editor/non-GM roles).

### 3.10 Front-desk reversal and printer workflow

- Explicit reversal workflow added via `POST /api/v1/folios/{folio_id}/reversals` for `front_desk` and `finance`.
- Manual charge posting workflow added via `POST /api/v1/folios/{folio_id}/charges` with required reason.
- Printer integration uses local queue abstraction:
  - `POST /api/v1/folios/{folio_id}/print` queues receipt payload into `data/print_queue/<org>/...`
  - Optional local dispatch adapter (`PRINT_COMMAND_TEMPLATE`) can handoff queue file to host spoolers/printers.
  - print queue artifacts are auditable and persisted (`PrintJob`).
- Invoice artifact and print path are explicit: `GET /api/v1/folios/{folio_id}/invoice`, `POST /api/v1/folios/{folio_id}/print-invoice`.

### 3.11 Order exception compensation

- Order creation includes explicit compensation handling: if processing fails after financial staging, a compensating folio adjustment entry and audit event are recorded before returning controlled error response.

## 4) Backend modular boundaries

- API routing composition: `backend/api/routes.py`
- Domain route modules:
  - `backend/api/routers/operations.py`
  - `backend/api/routers/engagement.py`
  - `backend/api/routers/folios.py`
  - `backend/api/routers/governance.py`
  - `backend/api/routers/orders.py`
- AuthN/AuthZ dependencies: `backend/api/deps.py`
- Domain services:
  - `services/auth.py`, `services/orders.py`, `services/folio.py`
  - `services/complaints.py`, `services/ratings.py`, `services/day_close.py`
  - `services/analytics.py`, `services/governance.py`, `services/exports.py`
- Shared utilities:
  - `core/config.py`, `core/security.py`, `core/logging.py`, `core/runtime_guard.py`

This separation keeps business logic in service modules while route handlers remain orchestration-focused.

List/read APIs apply bounded pagination (`limit`/`offset`) with optional filter/sort controls on operationally hot endpoints.

## 5) Frontend architecture

Frontend was refactored to reduce monolithic coupling:

- Route-level guards and role-aware routes via `frontend/src/router/index.js`
- API client abstraction: `frontend/src/api/client.js`
- Domain components:
  - `frontend/src/components/LoginPanel.vue`
  - `frontend/src/components/OrderComposer.vue`
  - `frontend/src/components/FolioOperationsPanel.vue`
  - `frontend/src/components/OrderOperationsPanel.vue`
  - `frontend/src/components/ReleasesAuditPanel.vue`
  - `frontend/src/components/ServiceDurationPanel.vue`
  - `frontend/src/components/ComplaintPanel.vue`
  - `frontend/src/components/ContentReleasePanel.vue`
  - `frontend/src/components/RatingsPanel.vue`
  - `frontend/src/components/GovernanceOpsPanel.vue`
  - `frontend/src/components/FinanceClosePanel.vue`
  - `frontend/src/components/CreditPanel.vue`
- Workflow composables:
  - `frontend/src/composables/useSessionLifecycle.js`
  - `frontend/src/composables/useFolioOps.js`
  - `frontend/src/composables/useOrderOps.js`
  - `frontend/src/composables/useDashboardData.js`
- Frontend integration coverage includes quote-reconfirm and folio-failure paths in `frontend/src/App.integration.test.js`.
- Browser E2E security coverage exists under `frontend/e2e/` (Playwright) for direct URL guard interception, lockout behavior, and idle-timeout logout behavior.
- Route-level view containers now map auth/workspace/finance/governance routes to dedicated view modules under `frontend/src/views/`.
- Guest ordering UI includes local offering presets (room service, amenity, late checkout, spa add-on), cart-based multi-item checkout, multi-spec inputs, delivery slot labels, order note cap alignment (250 chars), and optional 18% service-charge automation.
- Operations UI now exposes role-specific controls for folio operations, order transitions/split-merge, ratings, governance dataset/lineage registration, and night-audit/day-close execution.
- Sensitive narrative notes in credit profile timelines are now served through shared role-based masking policy (finance/GM unmasked; other allowed roles masked).
- Frontend now includes explicit quote reconfirm submit step, receipt/print actions, complaint packet export, content rollback controls, and credit-score profile/history views.
- Frontend blocks order submit on locally expired quote confirmation and surfaces complaint seven-day eligibility status before complaint submission.
- Session lifecycle includes frontend inactivity timeout warning and forced logout at 15 minutes of inactivity; login UI surfaces password policy and lockout countdown feedback.
- App shell composition remains in `frontend/src/App.vue` but high-change role workflows are extracted into dedicated panels for lower coupling.

## 6) Persistence and migration strategy

- ORM metadata lives in `backend/models/models.py` and is exported through `backend/models/__init__.py`.
- Alembic environment is configured in `backend/alembic/env.py`.
- Baseline migration aligns schema to ORM metadata.
- CI and local `run_tests.sh` include migration upgrade checks before tests.

## 7) Observability posture

Structured event logs categorize operational paths:

- `auth`: login failures/lockouts/session expiry
- `authz`: token/role denials
- `finance`: postings and transitions
- `export`: payload write and verification outcomes
- `analytics`: fallback behavior

Audit events remain persisted for business/security action trails.

## 8) Known implementation boundaries

- Printer adapter integration remains browser/OS mediated (printable payload + PDF output) rather than direct device drivers.
- Catalog browsing UX is functional but not yet a full merchandising hierarchy.
