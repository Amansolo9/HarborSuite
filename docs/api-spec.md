# HarborSuite API Specification

Base path: `/api/v1`

Implementation note: endpoints are served through dedicated domain router modules (`backend/api/routers/operations.py`, `backend/api/routers/orders.py`, `backend/api/routers/folios.py`, `backend/api/routers/engagement.py`, `backend/api/routers/governance.py`) with unchanged HTTP contracts.

## Authentication

### `POST /auth/login`
- Body: `username`, `password`
- Returns identity metadata and sets httpOnly session cookie (`harborsuite_session` by default)
- Response still includes bearer token for compatibility with non-browser clients
- Errors: `401` invalid credentials / lockout

### `GET /auth/me`
- Auth required
- Returns role/profile + session policy metadata

### `POST /auth/logout`
- Auth required
- Revokes current session and clears session cookie

Session policy note: backend enforces inactivity timeout and lockout; frontend mirrors this with local idle timer warning and lockout UX messaging.

## Operations and dashboards

### `GET /operations/overview`
- Auth required
- Returns organization-scoped KPI counters

### `GET /analytics/gm-dashboard`
- Roles: `general_manager`
- Returns churn/order volume/budget execution view (safe defaults when source unavailable)

### `GET /analytics/service-durations`
- Roles: `service_staff`, `finance`, `general_manager`
- Returns aggregated service duration metrics grouped by actor role and order type

### `POST /analytics/snapshots`
- Roles: `finance`, `general_manager`
- Explicitly records analytics snapshot payloads for supported sources (`gm_dashboard`, `service_durations`)

## Orders

### `POST /orders/confirm-quote`
- Roles: `guest`, `front_desk`
- Confirms quote snapshot and returns:
  - `reconfirm_token`
  - `quote_hash`
  - expiry timestamp (10-minute window)
- Snapshot includes items/specs, fees, tax rate, payment method, delivery window, and tax rule version
- Unit pricing is authoritative on backend catalog mapping (SKU/name to canonical price); tampered client prices are rejected

### `POST /orders`
- Roles: `guest`, `front_desk`
- Requires:
  - `reconfirm_token`
  - `price_confirmed_at`
  - `delivery_window_start`, `delivery_window_end`
  - item `unit_price` for each line
  - item specs (`size`, `specs`, optional `delivery_slot_label`)
  - optional `order_note` (max 250 chars)
- Validation:
  - token expiration
  - quote hash payload parity (drift detection)
  - reconfirm recency
  - delivery window validity
  - on processing exception after financial staging, backend records a compensating folio adjustment entry and audited compensation event
  - authoritative catalog pricing validation (rejects client price override)
- Errors: `409` for quote mismatch, expired reconfirm token, stale confirmation, or policy conflicts
- Frontend UX additionally enforces local quote-TTL boundary (10 minutes) and blocks submit when that boundary is elapsed.

### `GET /orders`
- Auth required
- Guest sees own orders; staff sees organization orders
- Query params: `state` (optional), `sort` (`created_desc`|`created_asc`), `limit` (1-200), `offset` (>=0)

### `POST /orders/{order_id}/transition`
- Roles: `front_desk`, `service_staff`, `finance`
- State machine transitions enforced
- Refund requires `reversal_reason`
- Service duration timestamps captured on prep/terminal transitions

### `POST /orders/{order_id}/split`
- Roles: `front_desk`, `service_staff`, `finance`
- Splits order dimensions by supplier/warehouse/SLA

### `POST /orders/{order_id}/merge`
- Roles: `front_desk`, `service_staff`, `finance`
- Consolidates to a single supplier/warehouse/SLA allocation

### `GET /orders/{order_id}/allocations`
- Auth required with org scoping
- Query params: `limit` (1-200), `offset` (>=0)

## Folios

### `GET /folios`
- Auth required; guest ownership scoped
- Query params: `status` (optional), `limit` (1-200), `offset` (>=0)

### `POST /folios/{folio_id}/payments`
- Roles: `front_desk`, `finance`
- Payment enum constrained: `cash`, `card_present_manual`, `gift_certificate`, `direct_bill`

### `POST /folios/{folio_id}/charges`
- Roles: `front_desk`, `finance`
- Posts manual `charge` entry with required `reason` and positive `amount`

### `POST /folios/{folio_id}/adjustments`
- Role: `finance`

### `POST /folios/{folio_id}/reversals`
- Roles: `front_desk`, `finance`
- Explicit reversal path with mandatory reason

### `POST /folios/{folio_id}/split`
- Roles: `front_desk`, `finance`

### `POST /folios/merge`
- Role: `finance`

### `GET /folios/{folio_id}/receipt`
- Auth required + resource authorization

### `POST /folios/{folio_id}/print`
- Roles: `front_desk`, `finance`
- Queues local receipt print job for on-prem print queue processing
- If `PRINT_COMMAND_TEMPLATE` is configured, print adapter attempts immediate OS/local-network dispatch and marks status accordingly

### `GET /folios/{folio_id}/invoice`
- Auth required + resource authorization

### `POST /folios/{folio_id}/print-invoice`
- Roles: `front_desk`, `finance`
- Queues/dispatches invoice print jobs via same local print adapter path

## Content governance

### `POST /content/releases`
- Role: `content_editor`
- Supports `content_type`: `announcement`, `news`, `carousel_promo`
- Supports targeting dimensions: `target_roles`, `target_tags`, `target_organizations`

### `GET /content/releases`
- Auth required (visibility filtering by role + audience tag targets)
- First read per user/release pair increments readership tracking
- Query params: `status` (optional), `limit` (1-200), `offset` (>=0)
- Non-editor/non-GM users only receive `approved` releases

### `POST /content/releases/{release_id}/approve`
- Role: `general_manager`

### `POST /content/releases/{release_id}/rollback`
- Roles: `content_editor`, `general_manager`

## Complaints and ratings

### `POST /complaints`
- Roles: `guest`, `service_staff`
- Enforces 7-day complaint window relative to related service order timeline
- Frontend additionally displays complaint eligibility window status before submit.

### `GET /complaints/{complaint_id}/packet`
- Roles: `guest`, `service_staff`, `finance`, `general_manager`
- Object controls: same-org required; `guest`/`service_staff` can only access packets they reported
- Generates/returns packet checksum metadata

### `POST /ratings`
- Auth required
- Requires `order_id`
- Enforces completed-order state and participant/role eligibility checks (`guest` <-> `service_staff`)
- `service_staff` must be the staff actor assigned to that order's service lifecycle

### `GET /ratings/me`
- Auth required
- Returns inbound/outbound ratings for current actor
- Query params: `limit` (1-200), `offset` (>=0)

## Day-close and audit

### `POST /night-audit/run`
- Roles: `finance`, `general_manager`
- Strict imbalance threshold `<= 0.01`
- Default scope is caller organization
- Cross-org scope requires explicit super-admin override (`organization_id` or `all_organizations`)

### `POST /day-close/run`
- Roles: `finance`, `general_manager`
- Executes day-close workflow with cutoff configuration, auto-post room/tax, and close-blocking on failed reconciliation
- Default scope is caller organization
- Cross-org scope requires explicit super-admin override (`organization_id` or `all_organizations`)

### `GET /audit/logs`
- Role: `general_manager`
- Organization-scoped audit events
- Query params: `sort` (`created_desc`|`created_asc`), `limit` (1-200), `offset` (>=0)

## Exports

### `POST /exports`
- Roles: `finance`, `general_manager`
- Writes local export payload file, verifies read-back checksum integrity, persists metadata path/checksum
- `export_type` is strict-pattern validated and path traversal payloads are rejected

## Governance metadata APIs

### `POST /governance/metrics`
- Role: `general_manager`

### `POST /governance/datasets`
- Roles: `finance`, `general_manager`

### `POST /governance/lineage`
- Roles: `finance`, `general_manager`

### `GET /governance/lineage`
- Roles: `finance`, `general_manager`
- Query params: `limit` (1-200), `offset` (>=0)

### `GET /governance/dictionary/export`
- Roles: `finance`, `general_manager`, `content_editor`

## Additional acceptance endpoints

### `POST /credit-score/calculate`
- Roles: `front_desk`, `finance`, `general_manager`

### `GET /credit-score/{username}`
- Roles: `front_desk`, `finance`, `general_manager`
- Event-note masking is role-aware (`finance`/`general_manager` can view full note; other allowed roles receive masked note text)
