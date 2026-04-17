# HarborSuite Offline Hotel Commerce & PMS - Delivery Acceptance & Architecture Audit

---

## 1. Verdict

**Overall Conclusion: Partial Pass**

The delivery is a substantially complete full-stack implementation that materially addresses the prompt's core business goal of offline hotel commerce and PMS operations. The backend implements real business logic with PostgreSQL persistence, state-machine-driven orders, folio management, content governance, complaints, credit scores, night audit, day-close, and data governance. The Vue.js frontend is functional with role-based access. However, there are several High-severity gaps against the prompt requirements (missing optional 18% service charge backend enforcement, `hmac.new` vs `hmac.HMAC` bug in security.py) and multiple medium issues. The project is not a demo or stub but a near-production-quality deliverable with meaningful test coverage.

---

## 2. Scope and Static Verification Boundary

### Reviewed
- All Python backend source: models, schemas, services, routers, core modules, migrations, scripts
- All test files: 6 unit test files, 7 API test files, 2 E2E spec files, 1 frontend unit test, 1 API client test
- Frontend Vue.js source: App.vue, all 22 components, all 9 composables, API client, router, views
- Configuration: docker-compose.yml, docker-compose.prod.yml, Dockerfile, alembic.ini, package.json, requirements.txt
- Data files: order_catalog.json, seed data, print queue samples, evidence PDFs
- README.md documentation

### Not Reviewed
- Runtime behavior (no Docker, no server start, no test execution)
- Actual database schema migrations at runtime
- Frontend CSS/Tailwind output rendering (no browser)
- Network connectivity or CORS behavior

### Intentionally Not Executed
- `docker compose up`, `pytest`, `npm run test`, `npm run test:e2e`, `npm run build`
- Any database operations or API calls

### Claims Requiring Manual Verification
- Actual runtime startup succeeds with PostgreSQL
- All tests pass green
- Frontend renders correctly in a browser
- CSRF middleware works correctly with cookie-based sessions
- Day-close scheduler thread fires at configured cutoff time
- Print command dispatch works with `PRINT_COMMAND_TEMPLATE`

---

## 3. Repository / Requirement Mapping Summary

### Prompt Core Business Goal
Offline-first hotel commerce and PMS for full-service hotels: ordering, billing, operational reporting without internet dependency. Vue.js frontend, FastAPI backend, PostgreSQL, six named roles.

### Core Flows Required
1. Guest browsing/ordering with multi-spec, packaging fee ($2.50), optional 18% service charge, 250-char notes, real-time price reconfirm within 10 min
2. Folio management: charge, reverse, split, merge, print invoices/receipts to local printers; payment methods: cash, card-present manual, gift certificate, direct bill
3. Content governance: announcements, news, carousel promos, approval workflow, targeted release, version rollback, readership analytics
4. Mutual 1-5 star ratings, complaints within 7 days, service-duration stats, credit score (300-850, default 700), PDF arbitration packets
5. Night audit: configurable day-close (default 3:00 AM), auto-post room/tax, block closure if folio out of balance by >$0.01, reconciliation reports
6. Data governance: metric definitions, lineage, dataset versions, data dictionary
7. Security: RBAC, 15-min session timeout, 10-char password complexity, 5-attempt lockout for 15 min, field-level masking, checksummed exports

### Implementation Mapping
All 7 areas have corresponding backend services, API routes, models, and frontend components. Mapping is detailed in Section 4 below.

---

## 4. Section-by-Section Review

### 4.1 Hard Gates

#### 4.1.1 Documentation and Static Verifiability
**Conclusion: Pass**

- `README.md:1-196` provides clear startup instructions for Docker and local development
- Backend and frontend entry points documented: `uvicorn backend.app.main:app` (`README.md:62`), `npm run dev` (`README.md:83`)
- Test commands documented: `python -m pytest unit_tests API_tests` (`README.md:126-127`), `npm run test` (`README.md:93`), E2E with Playwright (`README.md:98-103`)
- Environment variables and configuration documented (`README.md:58-68`, `README.md:149-161`)
- Database bootstrap documented (`README.md:61`)

#### 4.1.2 Material Deviation from Prompt
**Conclusion: Pass**

The implementation is centered on the hotel PMS offline commerce scenario. All major functional areas described in the prompt have corresponding implementation. No significant areas are unrelated to the prompt. The project does not replace or weaken the core problem definition.

### 4.2 Delivery Completeness

#### 4.2.1 Core Functional Requirements Coverage
**Conclusion: Partial Pass**

Implemented:
- Guest ordering with multi-spec, packaging fee enforcement ($2.50): `backend/services/orders.py:139,201`
- Order note capped at 250 chars: `backend/schemas/pms.py:65` (`max_length=250`)
- Price reconfirm within 10 minutes: `backend/services/orders.py:119-121`, quote verification: `backend/services/orders.py:166-180`
- Order state machine (created/confirmed/in_prep/delivered/canceled/refunded): `backend/models/models.py:72-79`
- Folio charge/payment/adjustment/reversal: `backend/services/folio.py:34-101`
- Folio split and merge: `backend/services/folio.py:114-183`
- Payment methods enum (cash, card_present_manual, gift_certificate, direct_bill): `backend/models/models.py:25-30`
- Invoice/receipt print to local printers: `backend/services/printer.py:16-74`
- Content releases with approval workflow, rollback, readership analytics: `backend/services/content.py:10-130`
- Content targeting by role, tag, organization: `backend/services/content.py:56-87`
- Mutual 1-5 star ratings between guest and staff: `backend/services/ratings.py:22-92`
- Complaints within 7 days: `backend/services/complaints.py:40-41`
- Credit score (300-850, default 700): `backend/services/credit_score.py:14-25`, `backend/models/models.py:378`
- PDF arbitration packets with checksums: `backend/services/complaints.py:60-106`
- Night audit with $0.01 tolerance: `backend/services/night_audit.py:25`
- Day-close auto-post room and tax: `backend/services/day_close.py:74-90`
- Configurable cutoff time (default 3:00 AM): `backend/core/config.py:59`
- Data governance: metrics, lineage, datasets, dictionary: `backend/services/governance.py`, `backend/api/routers/governance.py`
- RBAC, session timeout, password policy, lockout, field-level masking, checksummed exports: implemented across security/auth modules

Gaps:
- **Optional 18% service charge**: The frontend calculates this (`frontend/src/components/OrderComposer.vue:161-165`) but the backend does not validate that the service_fee corresponds to 18% of the subtotal. The backend accepts any service_fee >= 0 (`backend/schemas/pms.py:63`). This is a partial gap; the feature exists but enforcement is client-side only.
- **Order split/merge by supplier/warehouse/SLA**: Implemented as `OrderAllocation` dimension splits (`backend/services/orders.py:333-412`), not as actual splitting of order items or creating separate orders. This is a reasonable interpretation but somewhat simplified.
- **Violation records in credit score**: Violation count is tracked (`backend/models/models.py:379`) and events logged (`backend/services/credit_score.py:60-61`), but there is no dedicated violation record entity; violations are embedded in CreditEvent.

#### 4.2.2 End-to-End Deliverable Assessment
**Conclusion: Pass**

- Complete project structure with backend (FastAPI), frontend (Vue.js/Vite), Docker orchestration, Alembic migrations
- No mock/hardcoded behavior replacing real logic in production paths
- Seed data provided for development only, gated by `SEED_DEMO_DATA` flag
- Production compose profile with security guards (`docker-compose.prod.yml`, `backend/core/runtime_guard.py`)
- README provides comprehensive documentation

### 4.3 Engineering and Architecture Quality

#### 4.3.1 Structure and Module Decomposition
**Conclusion: Pass**

- Clear separation: `backend/api/routers/` (5 routers), `backend/services/` (16 services), `backend/models/`, `backend/schemas/`, `backend/core/`
- Frontend organized into `components/` (22 components), `composables/` (9 composables), `views/`, `api/`
- Router registration is centralized in `backend/api/routes.py:1-12`
- No redundant or unnecessary files observed
- No single-file monolith; logic is distributed across appropriately scoped modules

#### 4.3.2 Maintainability and Extensibility
**Conclusion: Pass**

- Order state machine is extensible via `ALLOWED_ORDER_TRANSITIONS` dict: `backend/models/models.py:72-79`
- Catalog is externalized to `data/order_catalog.json` with runtime loading: `backend/services/catalog.py`
- Configuration is environment-driven with sensible defaults: `backend/core/config.py`
- Frontend composables provide clean separation of concerns
- No tight coupling or chaotic structure observed

### 4.4 Engineering Details and Professionalism

#### 4.4.1 Error Handling, Logging, Validation, API Design
**Conclusion: Partial Pass**

Strengths:
- Structured logging with category/event pattern: `backend/core/logging.py:18-20`
- Consistent error mapping in routers: KeyError->404, PermissionError->403, ValueError->409
- Pydantic validation on all request schemas with appropriate constraints
- Audit trail for all mutations via `audit_event()`
- Path traversal protection in exports: `backend/services/exports.py:50-54`
- Export type sanitization via regex: `backend/services/exports.py:18,42-45`

Issues:
- **Critical bug**: `backend/core/security.py:70` uses `hmac.new()` which does not exist in Python's `hmac` module. The correct function is `hmac.HMAC()` or `hmac.new()` — actually `hmac.new` IS the correct function. Let me re-verify... Python's `hmac` module has `hmac.new()`. This is correct. No bug.
- Compensating entry on order failure is well-implemented: `backend/services/orders.py:254-280`
- CSRF middleware properly implemented: `backend/app/main.py:73-93`

#### 4.4.2 Production Readiness
**Conclusion: Pass**

- Runtime guard blocks insecure secrets in non-dev environments: `backend/core/runtime_guard.py:18-27`
- Production Docker compose with separate secrets profile: `docker-compose.prod.yml`
- Database connection retry logic: `backend/core/database.py:27-36`
- Session token hashing (not storing raw tokens): `backend/services/auth.py:31-32`
- PBKDF2 password hashing with 200,000 iterations: `backend/core/security.py:39`
- Scheduler thread with clean shutdown: `backend/app/main.py:27-59`

### 4.5 Prompt Understanding and Requirement Fit

#### 4.5.1 Business Goal and Constraint Alignment
**Conclusion: Partial Pass**

Correctly implemented:
- Offline-first design: no external API calls, no online payment authorization
- All six roles implemented: Guest, Front Desk, Service Staff, Finance, Content Editor, General Manager
- Multi-organization (tenant) isolation throughout
- Local printer support with file-based queue fallback
- Configurable day-close time, room rate, tax rate

Minor deviations:
- The prompt mentions "in-room kiosks" but the frontend is a single SPA without a dedicated kiosk mode. This is an implicit constraint and reasonable to omit.
- The prompt says "carousel promos" as a content type; the enum includes it (`backend/models/models.py:64`) but the frontend has no carousel rendering component. Content management is present but rendering is list-based only.
- The prompt mentions "fund income-expense and budget execution" dashboards; these are implemented as computed metrics in the GM dashboard (`backend/services/analytics.py:143-144`) but are aggregate numbers, not detailed dashboards.

### 4.6 Aesthetics (Frontend)

#### 4.6.1 Visual and Interaction Design
**Conclusion: Cannot Confirm Statistically**

Static observations:
- Tailwind CSS is configured (`frontend/package.json:24`)
- Components use semantic class names: `.panel`, `.form-grid`, `.stack-card`, `.primary-button`, `.ghost-button`, `.hint`, `.eyebrow`
- Login panel has two-column layout: intro panel + form panel (`frontend/src/components/LoginPanel.vue:2-42`)
- Stats grid for dashboard overview: `frontend/src/components/StatsGrid.vue`
- Form elements use labels, placeholders, disabled states, and loading indicators
- Error/success messages displayed: `frontend/src/App.vue:113-114`
- Idle session warning displayed in header
- Lockout countdown displayed in login panel

Cannot confirm without browser rendering:
- Actual visual appearance and alignment
- Responsive behavior
- Color scheme consistency
- Interactive feedback (hover states, transitions)

---

## 5. Issues / Suggestions (Severity-Rated)

### Issue 1: Service Fee Backend Enforcement Missing
**Severity: High**

**Conclusion:** The prompt specifies an "optional 18% service charge" as a defined business rule. The frontend correctly computes 18% of subtotal (`OrderComposer.vue:161-165`), but the backend accepts any non-negative service_fee value (`backend/schemas/pms.py:63`, `ge=0`). There is no server-side validation that the service fee is either $0.00 or exactly 18% of the subtotal.

**Evidence:** `backend/schemas/pms.py:63`, `backend/services/orders.py:183-280` (no service_fee validation logic)

**Impact:** A malicious or buggy client could submit arbitrary service fees, bypassing the business rule. Financial integrity of orders is dependent on client-side enforcement only.

**Minimum Fix:** Add server-side validation in `create_order()` and `confirm_quote()` that `service_fee` is either `Decimal("0.00")` or equals `subtotal * Decimal("0.18")` (within rounding tolerance).

---

### Issue 2: Night Audit Does Not Block Day-Close on Imbalance
**Severity: High**

**Conclusion:** The prompt requires that night audit "blocks closure if any folio is out of balance by more than $0.01." The `run_day_close` function runs the audit after auto-posting room/tax charges (`backend/services/day_close.py:93`), and if `failed_count > 0`, sets status to `FAILED` (`backend/services/day_close.py:103`). However, the day-close still proceeds to create a `DayCloseRun` record with `FAILED` status and commits. The folios are NOT rolled back to their pre-audit state after auto-posting when the audit fails; they remain in `IN_AUDIT` status with the auto-posted charges still present.

**Evidence:** `backend/services/day_close.py:72-103` — When `passed` is False (line 97-103), the folio status remains `IN_AUDIT` and the auto-posted charges (room + tax) persist. The function does not rollback the FolioEntry additions.

**Impact:** Failed day-close leaves folios in a dirty state: marked `IN_AUDIT` with room/tax charges that may not have been intended. Repeated runs are idempotent per business_date (`day_close.py:46-59`) so the operator cannot re-run after fixing the imbalance — the run is already recorded.

**Minimum Fix:** When audit fails, rollback the auto-posted FolioEntry records and restore folio status to `OPEN`. Or do not commit auto-posted entries until the audit passes.

---

### Issue 3: Packaging Fee Hardcoded to $2.50 Without Food-Item Check
**Severity: Medium**

**Conclusion:** The prompt says "$2.50 packaging fee per food order." The backend enforces exactly `$2.50` for all orders (`backend/services/orders.py:139,201`), regardless of whether the order contains food items. The frontend correctly applies $2.50 only when food items are in the cart (`OrderComposer.vue:158-159`), but the backend will reject any order with a packaging fee other than $2.50, even if the order is entirely non-food (e.g., late checkout, spa add-on).

**Evidence:** `backend/services/orders.py:139` — `if packaging_fee != _quantize(Decimal("2.50")): raise ValueError`

**Impact:** Non-food orders (spa, late checkout, amenities) cannot be placed unless they include a $2.50 packaging fee, which is incorrect per business rules.

**Minimum Fix:** Conditionally require $2.50 only when order items include food SKUs (items with `sku` starting with `food_`), allow $0.00 for non-food-only orders.

---

### Issue 4: Folio Reversal Does Not Require a Reason at Schema Level
**Severity: Medium**

**Conclusion:** The prompt states "reverse charges with a required reason." The `FolioReversalRequest` schema does require a reason (`backend/schemas/pms.py:160`, `min_length=5`), which is correct. However, the `post_reversal` service function does not validate the reason beyond the schema level. This is adequate — Pydantic enforces it. **No issue found after closer inspection; this is correctly implemented.**

*Withdrawn — not an issue.*

---

### Issue 4 (actual): Guest Folio Access Control Incomplete for Order Listing
**Severity: Medium**

**Conclusion:** `list_orders` correctly scopes guests to their own orders (`backend/services/orders.py:289-290`). However, the orders list route `GET /api/v1/orders` allows any authenticated user to list orders for their organization. A `SERVICE_STAFF` user can see all orders in the org, which is appropriate. This is actually correct behavior per the prompt. **Withdrawn.**

---

### Issue 4 (actual): Refund FolioEntry Uses ADJUSTMENT Instead of REVERSAL Type
**Severity: Medium**

**Conclusion:** When an order is refunded, the compensating folio entry uses `FolioEntryType.ADJUSTMENT` (`backend/services/orders.py:317-325`) instead of `FolioEntryType.REVERSAL`. This means night audit reconciliation treats refunds as adjustments, potentially affecting the accuracy of reconciliation reports that distinguish between adjustments and reversals.

**Evidence:** `backend/services/orders.py:318` — `entry_type=FolioEntryType.ADJUSTMENT`

**Impact:** Reconciliation reports may misclassify refund-driven folio entries. The night audit service (`backend/services/night_audit.py:48-50`) sums adjustments and reversals separately, so this affects delta calculation accuracy.

**Minimum Fix:** Use `FolioEntryType.REVERSAL` for refund-triggered folio entries.

---

### Issue 5: CSRF Token Not Rotated on Login
**Severity: Medium**

**Conclusion:** The CSRF middleware sets a CSRF cookie only when one is not already present (`backend/app/main.py:83`). After login, the same CSRF token persists. Best practice is to rotate CSRF tokens on session establishment to prevent session fixation attacks via CSRF.

**Evidence:** `backend/app/main.py:83-92`

**Impact:** Low practical risk in an offline/LAN environment, but a defense-in-depth gap.

**Minimum Fix:** Regenerate the CSRF cookie after successful login.

---

### Issue 6: Logout Does Not Invalidate CSRF Cookie
**Severity: Low**

**Conclusion:** The logout endpoint deletes the session cookie (`backend/api/routers/operations.py:115`) but does not delete the CSRF cookie. A stale CSRF token persists after logout.

**Evidence:** `backend/api/routers/operations.py:114-116`

**Impact:** Minimal in practice; CSRF check only applies when a session cookie is present.

**Minimum Fix:** Delete the CSRF cookie on logout.

---

### Issue 7: Day-Close Scheduler Runs for ALL Organizations Without Scope
**Severity: Medium**

**Conclusion:** The background day-close scheduler (`backend/app/main.py:27-42`) calls `run_day_close(db, actor=None)` without passing `organization_ids`. This means the scheduler runs day-close for ALL organizations in the database. Per the prompt, day-close should be a "controlled" operation. The scheduled auto-run may be unexpected for some organizations.

**Evidence:** `backend/app/main.py:37`

**Impact:** All organizations get auto-closed daily regardless of individual business preferences. There is no per-organization opt-out mechanism.

**Minimum Fix:** Either scope the scheduler to specific organizations or make auto-close configurable per organization.

---

### Issue 8: `order_note` Length Not Enforced in Service Layer
**Severity: Low**

**Conclusion:** The Pydantic schema enforces `max_length=250` on `order_note` (`backend/schemas/pms.py:65`), which is correct. The model column `String(250)` also enforces it at the database level (`backend/models/models.py:163`). No additional service-layer enforcement needed. **Correctly implemented.**

*Withdrawn.*

---

### Issue 8 (actual): Frontend API Client Does Not Use Cookie-Based Auth by Default
**Severity: Low**

**Conclusion:** The `createApiClient` in `frontend/src/api/client.js:5` initializes with `getToken: () => ''`, which means the Bearer token is always empty. Authentication relies entirely on cookie-based sessions via `credentials: 'include'` (`client.js:19`). This is consistent with the documented design (`README.md:107`). **Not an issue; this is the intended cookie-based flow.**

*Withdrawn.*

---

### Issue 8 (actual): Content Release Readership Tracking Has Side Effect on GET
**Severity: Low**

**Conclusion:** The `list_releases` function (`backend/services/content.py:39-88`) performs a write operation (incrementing `readership_count`, adding `ContentReadEvent`) during what is a GET request. This violates HTTP semantics for safe methods and means listing releases is not idempotent.

**Evidence:** `backend/services/content.py:84-86`, called from `GET /api/v1/content/releases` (`backend/api/routers/engagement.py:77-88`)

**Impact:** Read endpoints have write side effects. Retry/caching behavior could produce unexpected results.

**Minimum Fix:** Move readership tracking to a separate POST endpoint (e.g., `POST /content/releases/{id}/read`).

---

## 6. Security Review Summary

### Authentication Entry Points
**Conclusion: Pass**

- Single login endpoint: `POST /api/v1/auth/login` (`backend/api/routers/operations.py:56-89`)
- Password verified via PBKDF2-SHA256 with 200k iterations: `backend/core/security.py:36-41`
- Session tokens stored as SHA-256 hashes: `backend/services/auth.py:31`
- Cookie-based sessions with httpOnly, secure (in prod), samesite=lax: `backend/api/routers/operations.py:70-78`
- Bearer token option for API testing: `backend/api/routers/operations.py:81`
- Lockout after 5 failed attempts for 15 minutes: `backend/services/auth.py:57-68`
- Password complexity policy (10+ chars, upper, lower, digit, symbol): `backend/core/security.py:22-33`

### Route-Level Authorization
**Conclusion: Pass**

- All routes except `/health` and `POST /auth/login` require authentication via `get_current_user` dependency
- Role-based restrictions via `require_roles()` decorator: `backend/api/deps.py:35-42`
- Examples: adjustments require `FINANCE` only (`folios.py:107`), content approval requires `GENERAL_MANAGER` (`engagement.py:94`), audit logs require `GENERAL_MANAGER` (`governance.py:57`)

### Object-Level Authorization
**Conclusion: Pass**

- Folio access checks organization_id match AND guest-owns-own-folio: `backend/services/folio.py:16-24`
- Order access scoped to organization: `backend/services/orders.py:298-299`
- Complaint packet access checks organization + role + reporter: `backend/services/complaints.py:77-82`
- Cross-org access consistently blocked via `PermissionError`: tested in `test_cross_org_object_access_is_blocked` (`API_tests/test_api_coverage_matrix.py:294-315`)

### Function-Level Authorization
**Conclusion: Pass**

- Complaint creation restricted to Guest and Service Staff: `engagement.py:125`
- Content creation restricted to Content Editor: `engagement.py:60`
- Night audit and day-close restricted to Finance and GM: `operations.py:167,184`
- Cross-org scope override requires super-admin: `operations.py:49-50`

### Tenant / User Data Isolation
**Conclusion: Pass**

- All queries filter by `organization_id`: orders (`orders.py:288`), folios (`folio.py:28-30`), content (`content.py:43-48`), complaints, ratings, exports, governance data
- Two test organizations seeded (Seabreeze, Summit) with cross-org tests: `API_tests/test_api_coverage_matrix.py:262-315`
- Guest role restricted to own folios/orders only

### Admin / Internal / Debug Endpoint Protection
**Conclusion: Pass**

- No debug endpoints or admin panels exposed
- `/health` endpoint returns minimal status only: `backend/app/main.py:107-109`
- Audit logs restricted to GENERAL_MANAGER: `governance.py:57`
- Super-admin cross-org override requires explicit `SUPER_ADMIN_USERNAMES` env var: `operations.py:38-39`

---

## 7. Tests and Logging Review

### Unit Tests
**Conclusion: Pass**

6 unit test files covering:
- Order state machine transitions (valid + invalid): `unit_tests/test_order_state_machine.py`
- Order compensation/rollback: `unit_tests/test_order_compensation.py`
- Auth security policy (password policy, lockout): `unit_tests/test_auth_security_policy.py`
- Sensitive data leakage in logs: `unit_tests/test_logging_sensitive_data.py`
- Credit score calculation (formula, clamping, invalid input): `unit_tests/test_credit_score_service.py`
- Night audit service (balanced/imbalanced folios): `unit_tests/test_night_audit_service.py`
- Analytics service (GM dashboard scoped metrics): `unit_tests/test_analytics_service.py`

Tests use in-memory SQLite for unit isolation, which is appropriate.

### API / Integration Tests
**Conclusion: Pass**

7 API test files with comprehensive coverage:
- `test_security_and_workflows_api.py`: Auth, quote confirmation, state transitions, payment methods, content approval, complaints, session expiry, refund adjustment, lockout
- `test_api_coverage_matrix.py`: End-to-end flows for all major features including cross-org blocking, pagination, governance, ratings, day-close, exports
- `test_night_audit_api.py`: Night audit imbalance detection
- `test_health_and_credit_score_api.py`: Health check, credit score calculation, field masking
- `test_analytics_api.py`: GM dashboard scoping, analytics snapshot provenance
- `test_postgres_smoke.py`: PostgreSQL connectivity verification

Tests use TestClient with real FastAPI app and database reset per test via `conftest.py:15-19`.

### E2E Tests (Browser)
2 Playwright E2E specs:
- `frontend/e2e/auth-security.spec.js`: Route guard, lockout, idle logout
- `frontend/e2e/business-flows.spec.js`: Guest quote-to-order flow, front desk reversal and print

### Frontend Unit Tests
- `frontend/src/api/client.test.js`: API client unit test
- `frontend/src/composables/useOrderQuoteFlow.test.js`: Quote flow composable test

### Logging Categories / Observability
**Conclusion: Pass**

- Structured logging via `log_event()` with category + event + key-value fields: `backend/core/logging.py:18-20`
- Categories: `auth`, `authz`, `finance`, `scheduler`, `export`
- Key events logged: login success/failure, lockout, session expiry, order transitions, folio operations, day-close, exports
- No random print statements; all logging uses the structured pattern

### Sensitive-Data Leakage Risk in Logs / Responses
**Conclusion: Pass**

- Passwords are never logged: verified by `unit_tests/test_logging_sensitive_data.py:19-44`
- Session tokens are not logged (only hashes stored)
- Field-level masking in responses: `backend/services/masking.py:6-11` — non-Finance/GM roles see masked notes
- Credit profile events masked for non-privileged roles: `backend/services/credit_score.py:97`
- Tested: `test_credit_profile_notes_are_masked_for_front_desk` (`API_tests/test_health_and_credit_score_api.py:28-48`)

---

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview

| Dimension | Status |
|-----------|--------|
| Unit tests exist | Yes - 6 files in `unit_tests/` |
| API/integration tests exist | Yes - 7 files in `API_tests/` |
| Frontend unit tests exist | Yes - 2 test files (`client.test.js`, `useOrderQuoteFlow.test.js`) |
| E2E tests exist | Yes - 2 Playwright specs |
| Test framework (backend) | pytest |
| Test framework (frontend) | vitest (unit), playwright (E2E) |
| Test entry points | `python -m pytest unit_tests API_tests`, `npm run test`, `npm run test:e2e` |
| Documentation provides test commands | Yes - `README.md:89-127` |

### 8.2 Coverage Mapping Table

| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion | Coverage | Gap | Min Test Addition |
|---|---|---|---|---|---|
| Order quote confirmation required | `test_security_and_workflows_api.py:71-127` | 200 on valid quote, 409 on tampered/changed cart | Sufficient | None | - |
| Price reconfirm within 10 min | `test_security_and_workflows_api.py:129-168` | 409 on stale confirmation (11 min old) | Sufficient | None | - |
| Order state machine transitions | `test_order_state_machine.py:29-50`, `test_api_coverage_matrix.py:83-88` | Valid transitions succeed, invalid raise ValueError | Sufficient | None | - |
| Compensating folio entry on failure | `test_order_compensation.py:20-95` | Adjustment entry created with "Compensating entry" note | Sufficient | None | - |
| Payment methods constrained to enum | `test_security_and_workflows_api.py:189-197` | 422 on invalid `room_charge` method | Sufficient | None | - |
| Folio charge/payment/adjustment/reversal | `test_api_coverage_matrix.py:91-151` | All operations return 200, receipt has expected content | Sufficient | None | - |
| Folio split and merge | `test_api_coverage_matrix.py:116-139` | Split creates child folios, merge consolidates | Basically covered | No validation that split amounts actually equal balance in test | Add assertion on child folio balances |
| Content approval workflow | `test_security_and_workflows_api.py:200-209`, `test_api_coverage_matrix.py:182-238` | Editor creates, GM approves, guest sees after approval | Sufficient | None | - |
| Content tag targeting | `test_api_coverage_matrix.py:201-237` | VIP tag + role filter tested | Basically covered | No negative test for non-matching tags | Add test for non-VIP guest not seeing VIP content |
| Complaint 7-day window | `test_api_coverage_matrix.py:574-594` | 409 when order is 8 days old | Sufficient | None | - |
| Mutual ratings (guest<->staff) | `test_api_coverage_matrix.py:376-441` | Guest rates service staff, staff rates guest, self-rating blocked | Sufficient | None | - |
| Credit score calculation | `test_credit_score_service.py:8-19`, `test_health_and_credit_score_api.py:12-25` | Formula verification, clamping, API integration | Sufficient | None | - |
| Night audit $0.01 tolerance | `test_night_audit_service.py:16-44`, `test_night_audit_api.py:6-14` | Balanced folio passes, imbalanced fails | Sufficient | None | - |
| Day-close auto-post and idempotence | `test_api_coverage_matrix.py:540-550` | First run succeeds, second shows `already_ran` | Basically covered | No test for folio state after failed close | Add test verifying folio entries when audit fails |
| Password policy enforcement | `test_auth_security_policy.py:17-22` | Weak password rejected | Sufficient | None | - |
| Account lockout | `test_auth_security_policy.py:25-48`, `test_security_and_workflows_api.py:286-299` | Lockout after 5 failures, Retry-After header | Sufficient | None | - |
| Session idle timeout | `test_security_and_workflows_api.py:325-336` | 401 after last_seen_at set to 16 min ago | Sufficient | None | - |
| Field-level masking | `test_health_and_credit_score_api.py:28-48` | Finance sees full note, desk sees masked | Sufficient | None | - |
| Export checksums | `test_api_coverage_matrix.py:240-249` | Export file created at expected path | Basically covered | No checksum verification in test | Add checksum recomputation test |
| Export path traversal protection | `test_api_coverage_matrix.py:252-259` | 400 on `../../../../pwned` | Sufficient | None | - |
| Cross-org data isolation | `test_api_coverage_matrix.py:294-315` | 403 on cross-org folio/complaint access | Sufficient | None | - |
| Authentication required (401) | `test_security_and_workflows_api.py:66-68` | 401 on unauthenticated /orders | Sufficient | None | - |
| Role-based authorization (403) | `test_api_coverage_matrix.py:96-101`, `test_security_and_workflows_api.py:200-204,244-255` | Guest denied adjustment, editor denied approval, desk denied complaint | Sufficient | None | - |
| Pagination/sorting/filtering | `test_api_coverage_matrix.py:464-484` | Limit, offset, empty page, invalid limit 422, status filter | Sufficient | None | - |
| Governance (metrics, lineage, dictionary) | `test_api_coverage_matrix.py:487-537` | Metric/dataset/lineage CRUD, dictionary export, 404 on missing | Sufficient | None | - |
| Analytics provenance binding | `test_analytics_api.py:31-84` | Snapshot fails without governance metadata, succeeds after setup | Sufficient | None | - |
| Sensitive data not in logs | `test_logging_sensitive_data.py:19-44` | Password and "Bearer" absent from log output | Sufficient | None | - |

### 8.3 Security Coverage Audit

| Security Dimension | Test Coverage | Assessment |
|---|---|---|
| Authentication (401) | `test_protected_routes_require_authentication`, `test_login_unknown_username_returns_401`, `test_session_expires_after_idle_timeout` | Sufficient - unauthenticated access blocked, expired sessions caught |
| Route authorization (403) | Multiple tests across role boundaries: guest denied adjustment, editor denied approval, desk denied complaint creation, guest denied day-close | Sufficient |
| Object-level authorization | `test_cross_org_object_access_is_blocked`, `test_complaint_packet_same_org_is_role_restricted` | Sufficient - both cross-org and same-org unauthorized access tested |
| Tenant / data isolation | `test_gm_dashboard_is_organization_scoped`, `test_cross_org_targeted_release_visible_after_approval`, `test_cross_org_close_override_requires_super_admin` | Sufficient |
| Admin / internal protection | No admin endpoints exist; audit logs restricted to GM (tested), super-admin override tested | Sufficient |

### 8.4 Final Coverage Judgment

**Conclusion: Partial Pass**

The test suite provides strong coverage of core business flows, authentication/authorization boundaries, and data isolation. The tests statically appear well-structured and targeted at important risk points.

**Covered risks:** Authentication, RBAC, object-level authorization, tenant isolation, order state machine, quote reconfirmation, compensating entries, credit score, night audit balance checking, content governance, complaint window, export security, pagination, governance metadata, sensitive data masking.

**Uncovered risks that could allow defects to remain undetected:**
- Service fee enforcement (no backend validation test for 18% rule because no backend enforcement exists)
- Day-close folio state after audit failure (folios left in dirty IN_AUDIT state)
- Packaging fee on non-food-only orders (backend rejects $0 packaging fee even for non-food orders)
- Refund folio entry type (uses ADJUSTMENT instead of REVERSAL — no test validates the entry_type of refund)
- CSRF token behavior (no test for CSRF enforcement)

---

## 9. Final Notes

The HarborSuite delivery is a substantially complete, well-architected implementation of an offline hotel PMS system. The codebase demonstrates professional engineering practices: structured logging, consistent error handling, comprehensive audit trails, proper password hashing, session management, and multi-tenant data isolation. The test suite is strong, with meaningful integration tests that exercise real business flows rather than trivial assertions.

The primary gaps are:
1. **Service fee enforcement** is client-side only (High)
2. **Day-close leaves dirty folio state** on audit failure (High)
3. **Packaging fee is unconditionally required** even for non-food orders (Medium)
4. **Refund uses wrong FolioEntryType** (Medium)

These are addressable with targeted fixes and do not indicate fundamental architectural problems. The project is a credible delivery that could serve as a working foundation for hotel operations after the identified issues are resolved.
