# HarborSuite Offline Hotel Commerce & PMS - Delivery Acceptance & Architecture Audit

---

## 1. Verdict

**Overall Conclusion: Partial Pass**

The project delivers a materially complete, well-structured full-stack implementation of an offline hotel PMS with real business logic, PostgreSQL persistence, RBAC, audit trails, and a Vue.js frontend. Core business flows (orders, folios, content governance, complaints, night audit, credit scoring, ratings) are implemented with real state-machine logic, not mocks. The test suite is meaningful and covers critical paths. However, several medium/high-severity gaps exist: the CSRF middleware has an ordering issue with CORS, there is no frontend CSS/styling file included (only Tailwind configured), and a few prompt-specified requirements lack full implementation depth (e.g., real-time price re-confirmation UI flow, service-charge configurability).

---

## 2. Scope and Static Verification Boundary

### Reviewed
- All Python backend source files (models, services, routers, schemas, config, security, logging, migrations)
- All test files: 6 unit test files, 6 API integration test files, 2 E2E Playwright specs, 5 frontend unit/integration tests
- Frontend: all Vue components, composables, router, API client, package.json, vite config
- Docker configuration (docker-compose.yml, docker-compose.prod.yml, Dockerfile)
- README.md, data files, scripts

### Not Reviewed
- node_modules internals (standard dependency review excluded)
- Binary outputs (PDF evidence files)
- Alembic migration execution behavior

### Not Executed
- No Docker containers started
- No tests run
- No backend/frontend servers started
- No database connections made

### Claims Requiring Manual Verification
- Runtime behavior of CSRF middleware ordering with CORS
- Actual PostgreSQL migration execution
- Frontend visual rendering and layout quality
- Printer dispatch subprocess behavior
- Day-close scheduler thread timing accuracy

---

## 3. Repository / Requirement Mapping Summary

### Prompt Core Business Goal
Offline hotel PMS for full-service hotels with on-property ordering, billing, and operational reporting without internet dependency.

### Core Flows Required
1. Guest browsing/ordering with multi-spec, packaging fees ($2.50), optional 18% service charge, 250-char notes, real-time price re-confirmation within 10 minutes
2. Front Desk folio management: charge, reverse (with reason), split, merge, print invoices/receipts
3. Payment methods: cash, card-present manual, gift certificate, direct bill (no online auth)
4. Content governance: announcements/news/promos with approval workflow, targeted release, rollback, readership analytics
5. Mutual 1-5 star ratings (guest/staff) with 7-day window, complaints with PDF arbitration packets
6. Credit score system (300-850, default 700) with violation records
7. Night audit / day-close: configurable cutoff (default 3 AM), auto-post room+tax, block closure on imbalance > $0.01, reconciliation reports
8. Data governance: metric definitions, lineage, dataset versions, data dictionary
9. Security: RBAC, 15-min session timeout, password rules (10+ chars with complexity), lockout after 5 failures for 15 minutes, field-level masking, export checksums

### Implementation Mapping
| Requirement | Backend | Frontend | Tests |
|---|---|---|---|
| Order state machine | `services/orders.py` | `OrderComposer.vue`, `OrderOperationsPanel.vue` | Unit + API |
| Quote re-confirmation | `services/orders.py:124-181` | `QuoteReconfirmPanel.vue`, `useOrderQuoteFlow.js` | API test |
| Folio CRUD + split/merge | `services/folio.py` | `FolioOperationsPanel.vue` | API test |
| Payment methods | `models/models.py:25-29` | `OrderComposer.vue` | API test |
| Content governance | `services/content.py` | `ContentReleasePanel.vue`, `ReleasesAuditPanel.vue` | API test |
| Ratings (mutual) | `services/ratings.py` | `RatingsPanel.vue` | API test |
| Complaints + PDF | `services/complaints.py` | `ComplaintPanel.vue` | API test |
| Credit score | `services/credit_score.py` | `CreditPanel.vue` | Unit + API |
| Night audit | `services/night_audit.py` | `FinanceClosePanel.vue` | Unit + API |
| Day close | `services/day_close.py` | `FinanceClosePanel.vue` | API test |
| Data governance | `services/governance.py` | `GovernanceOpsPanel.vue` | API test |
| Auth/RBAC/lockout | `services/auth.py`, `core/security.py` | `LoginPanel.vue`, router guards | Unit + API + E2E |
| Session timeout | `services/auth.py:94-120` | `useSessionLifecycle.js` | API + E2E |
| Field masking | `services/masking.py` | `useDisplayUtils.js` | API test |
| Export checksums | `services/exports.py` | `ExportBundlePanel.vue` | API test |
| Local printing | `services/printer.py` | `FolioOperationsPanel.vue` | API test |

---

## 4. Section-by-Section Review

### 4.1 Hard Gates

#### 4.1.1 Documentation and Static Verifiability
**Conclusion: Pass**

- `README.md` provides clear startup instructions for Docker and local dev (`README.md:6-76`)
- Test commands documented (`README.md:111-147`)
- Demo credentials documented (`README.md:149-155`)
- Security runtime guard documented (`README.md:157-161`)
- Entry points are statically consistent: `backend/app/main.py` -> `backend/api/routes.py` -> 5 routers

#### 4.1.2 Prompt Alignment
**Conclusion: Pass**

The implementation is centered on the exact business scenario described: offline hotel PMS with ordering, billing, folios, content governance, complaints, ratings, credit scoring, night audit, and data governance. No major parts are unrelated or loosely coupled to the prompt. The system does not replace or weaken the core problem definition.

### 4.2 Delivery Completeness

#### 4.2.1 Core Requirement Coverage
**Conclusion: Partial Pass**

All explicitly stated core functional requirements are implemented with real logic:
- Order state machine with all 6 states (`models/models.py:71-78`)
- $2.50 packaging fee enforcement (`services/orders.py:139-140,201-202`)
- 18% optional service charge (frontend `OrderComposer.vue:73-75,158-163`)
- 250-char order note cap (`schemas/pms.py:65`)
- 10-minute price re-confirmation window (`services/orders.py:119-121,157`)
- Folio split/merge/charge/reversal/payment (`services/folio.py`)
- 4 offline payment methods (`models/models.py:25-29`)
- Content approval workflow with targeted release (`services/content.py`)
- 7-day complaint window (`services/complaints.py:40-41`)
- PDF arbitration packets (`services/complaints.py:60-71`)
- Credit score 300-850, default 700 (`services/credit_score.py:14-25`, `models/models.py:378`)
- Night audit with $0.01 tolerance (`services/night_audit.py:25,49`)
- Day-close configurable at 3:00 AM default (`core/config.py:59`)
- Data governance: metrics, lineage, datasets, dictionary (`services/governance.py`, `api/routers/governance.py`)
- RBAC with 6 roles (`models/models.py:16-22`)
- 15-min session timeout (`core/config.py:53`, `services/auth.py:105`)
- 10+ char password with complexity (`core/security.py:22-33`)
- Lockout after 5 failures for 15 minutes (`core/config.py:54-55`, `services/auth.py:57-68`)
- Field-level masking (`services/masking.py`)
- Export checksums (`services/exports.py:21-23`)

**Gap**: Reversal "required reason" is enforced only for refund transitions, not for general folio reversals (the schema requires min 5 chars on `FolioReversalRequest.reason` at `schemas/pms.py:160` but the folio service does not validate reason presence independently - schema validation suffices).

#### 4.2.2 End-to-End Deliverable
**Conclusion: Pass**

- Complete project structure with clear separation: backend (models/services/routers/schemas/core), frontend (components/composables/views/router)
- Docker Compose for deployment (`docker-compose.yml`, `docker-compose.prod.yml`)
- Database migrations (`backend/alembic/`)
- Seed data for demo (`backend/services/seed.py`)
- README with setup instructions
- No mock/hardcoded behavior replacing real logic - all business logic is implemented against the database

### 4.3 Engineering and Architecture Quality

#### 4.3.1 Structure and Module Decomposition
**Conclusion: Pass**

- Clear layered architecture: `models` -> `services` -> `api/routers` -> `schemas`
- Frontend: views -> composables -> components with clean separation of concerns
- 17 service modules, each with focused responsibility
- 5 API routers organized by domain (operations, orders, folios, engagement, governance)
- No excessive file bloat or unnecessary files
- No single monolithic file - the largest file (`App.vue`) is the main orchestrator which delegates to 12+ composables

#### 4.3.2 Maintainability and Extensibility
**Conclusion: Pass**

- Order state machine is cleanly defined with `ALLOWED_ORDER_TRANSITIONS` map (`models/models.py:71-78`)
- Role-based access is implemented via reusable `require_roles()` dependency (`api/deps.py:35-42`)
- Configuration externalized via environment variables (`core/config.py`)
- Service layer is testable with dependency injection (SQLAlchemy session passed through)
- Frontend composables provide reusable business logic hooks

### 4.4 Engineering Details and Professionalism

#### 4.4.1 Error Handling, Logging, Validation, API Design
**Conclusion: Pass**

- Structured logging with `category` and `event` fields (`core/logging.py:18-20`)
- Comprehensive audit trail via `AuditEvent` model (`services/audit.py`)
- Pydantic schema validation on all API inputs with field constraints (`schemas/pms.py`)
- Error handling maps exceptions to appropriate HTTP status codes (404/403/409/422)
- Password policy enforcement (`core/security.py:22-33`)
- Export path traversal protection (`services/exports.py:42-54`)
- CSRF middleware implemented (`backend/app/main.py:69-89`)

#### 4.4.2 Product Readiness
**Conclusion: Pass**

- Production compose profile with secure defaults (`docker-compose.prod.yml`)
- Runtime guard blocks insecure secrets in non-dev environments (`core/runtime_guard.py`)
- Session management with httpOnly cookies (`backend/app/main.py:70-78`, `api/routers/operations.py:70-78`)
- Data isolation by organization_id on all queries
- Multi-tenancy with 2 demo organizations

### 4.5 Prompt Understanding and Requirement Fit

#### 4.5.1 Business Goal Implementation
**Conclusion: Pass**

- Core business objective (offline hotel commerce and PMS) is correctly implemented
- No obvious misunderstandings of requirement semantics
- Key constraints respected: offline-first design, no online payment authorization, local printer adapter, configurable night audit cutoff

**Minor observation**: The prompt mentions "member scale/churn, event volume/participation, fund income-expense and budget execution, and approval efficiency" dashboards. These are all implemented in `services/analytics.py:80-159` as the `gm_dashboard` method returning `scale_index`, `churn_rate`, `participation_rate`, `order_volume`, `fund_income_expense`, `budget_execution`, and `approval_efficiency`.

### 4.6 Aesthetics (Frontend)

#### 4.6.1 Visual and Interaction Design
**Conclusion: Cannot Confirm Statistically**

- Vue.js components exist for all major functional areas (17+ components)
- Tailwind CSS is configured (`package.json` devDependencies)
- Components use semantic HTML structure with `<article>`, `<section>`, `<form>` elements
- Login panel, stats grid, live data panels, and operational panels are well-structured
- Role-based UI visibility is implemented via `useRoleAccess.js`
- Idle session warning countdown implemented (`useSessionLifecycle.js:78-98`)
- Lockout countdown displayed on login
- **Cannot confirm visual rendering quality** without running the frontend. No screenshots or static CSS file was found in `src/` directory - styling appears to depend entirely on Tailwind utility classes embedded in components (which were not fully reviewed in every component).

---

## 5. Issues / Suggestions (Severity-Rated)

### Issue 1: CSRF Middleware Ordering May Conflict with CORS Preflight
**Severity: Medium**

**Conclusion**: The CSRF middleware is added after the CORS middleware in `main.py:92-99`, but Starlette processes middleware in reverse addition order (LIFO). This means CSRF runs before CORS, which could block legitimate preflight OPTIONS requests.

**Evidence**: `backend/app/main.py:92-99`

**Impact**: OPTIONS preflight requests from the browser may receive a 403 CSRF error if they include session cookies, potentially blocking all cross-origin API requests from the frontend.

**Minimum Actionable Fix**: Add `OPTIONS` to `CSRF_SAFE_METHODS` set at `main.py:66`, or reorder middleware to ensure CORS processes before CSRF.

### Issue 2: CSRF Token Not Sent in Frontend API Client
**Severity: High**

**Conclusion**: The backend CSRF middleware (`main.py:69-89`) requires a `x-csrf-token` header matching the `harborsuite_csrf` cookie for all mutating requests when a session cookie is present. However, the frontend API client (`frontend/src/api/client.js:1-58`) never reads the CSRF cookie or sends the `x-csrf-token` header.

**Evidence**: `backend/app/main.py:72-77` (CSRF check), `frontend/src/api/client.js:8-16` (headers sent - no CSRF token)

**Impact**: All POST/PUT/DELETE requests from the Vue.js frontend that use cookie-based authentication will receive 403 "CSRF token missing or invalid" responses. This effectively blocks the primary cookie-auth flow documented in the README.

**Minimum Actionable Fix**: In `client.js`, read the `harborsuite_csrf` cookie and include it as `x-csrf-token` header on non-GET requests.

### Issue 3: No Dedicated Folio Reversal Entry Type
**Severity: Low**

**Conclusion**: The prompt specifies "post and reverse charges with a required reason." The implementation uses `FolioEntryType.ADJUSTMENT` for reversals (`services/folio.py:92`) with a "Reversal:" note prefix, rather than a dedicated `REVERSAL` entry type. This is a design choice that conflates adjustments and reversals in reporting.

**Evidence**: `models/models.py:38-41` (only CHARGE/PAYMENT/ADJUSTMENT), `services/folio.py:87-101`

**Impact**: Night audit and reconciliation reports cannot distinguish between manual adjustments and charge reversals without parsing note text. Low severity because the financial effect is correct.

**Minimum Actionable Fix**: Add a `REVERSAL` entry type to `FolioEntryType` enum and use it in `post_reversal`.

### Issue 4: Day-Close Scheduler Uses Minute-Level Polling
**Severity: Low**

**Conclusion**: The day-close scheduler loop (`main.py:27-38`) checks `now.hour == cutoff_hour and now.minute == cutoff_minute` every 60 seconds. This could miss the cutoff if the loop sleeps across the target minute boundary.

**Evidence**: `backend/app/main.py:30-31,38`

**Impact**: Day-close could fail to trigger on the exact configured minute. The risk is mitigated by the manual day-close API endpoint.

**Minimum Actionable Fix**: Use a more robust scheduling approach (e.g., check if `now >= cutoff` and cutoff hasn't already run today).

### Issue 5: Seed Data Contains Order Not Created Through Quote Flow
**Severity: Low**

**Conclusion**: The seed data creates an order directly without an associated `OrderQuote` record (`services/seed.py:62-91`). This is acceptable for demo seeding but creates an inconsistency if quote validation is retroactively checked.

**Evidence**: `backend/services/seed.py:62-91`

**Impact**: Minimal - seed data is only loaded in dev mode.

### Issue 6: Frontend Builds Local Catalog Fallback That May Diverge
**Severity: Medium**

**Conclusion**: The `OrderComposer.vue` contains a hardcoded `DEFAULT_CATALOG` (`OrderComposer.vue:116-121`) used as fallback when the API catalog endpoint fails. These prices could diverge from `data/order_catalog.json`, causing price mismatch errors at order submission.

**Evidence**: `frontend/src/components/OrderComposer.vue:116-121`, `backend/services/orders.py:53-59` (price validation)

**Impact**: If the catalog API is unavailable at page load, the guest could compose a cart with stale prices that will be rejected at quote confirmation.

**Minimum Actionable Fix**: Remove the fallback catalog or mark it clearly as offline-only with a user warning.

### Issue 7: `print_command_template` Allows Potential Command Injection
**Severity: Medium**

**Conclusion**: The printer service validates the file path with a regex (`services/printer.py:21`) but performs string replacement on the template (`printer.py:22`) before splitting with `shlex.split`. A malicious `PRINT_COMMAND_TEMPLATE` environment variable could contain injection payloads.

**Evidence**: `backend/services/printer.py:17-28`

**Impact**: Low in practice since `PRINT_COMMAND_TEMPLATE` is an environment variable controlled by the administrator, not user input. The file path is also validated with a restrictive regex. But the pattern is fragile.

**Minimum Actionable Fix**: Use parameterized subprocess call instead of string template replacement.

---

## 6. Security Review Summary

### Authentication Entry Points
**Conclusion: Pass**

- Single login endpoint: `POST /api/v1/auth/login` (`api/routers/operations.py:56-89`)
- Password verification uses PBKDF2-SHA256 with 200,000 iterations and random salt (`core/security.py:36-41`)
- Session tokens stored as SHA-256 hashes in the database (`services/auth.py:31-32`)
- httpOnly, Secure, SameSite=lax cookies (`api/routers/operations.py:70-78`)
- Lockout after 5 failed attempts for 15 minutes (`services/auth.py:57-68`)
- Runtime guard blocks insecure secrets in non-dev environments (`core/runtime_guard.py`)

### Route-Level Authorization
**Conclusion: Pass**

- All authenticated routes use `Depends(get_current_user)` or `Depends(require_roles(...))` (`api/deps.py`)
- Role restrictions are consistent with prompt requirements:
  - Orders: Guest + Front Desk for creation, Front Desk + Service Staff + Finance for transitions
  - Folios: Front Desk + Finance for mutations, Finance only for adjustments
  - Content: Content Editor for creation, General Manager for approval
  - Complaints: Guest + Service Staff
  - Night audit/day-close: Finance + General Manager
  - Audit logs: General Manager only
  - Credit score: Front Desk + Finance + General Manager

### Object-Level Authorization
**Conclusion: Pass**

- Organization-scoped queries on all resources (`services/folio.py:21`, `services/orders.py:298-299`, `services/content.py:97`, `services/complaints.py:77-78`)
- Guest users restricted to their own folios (`services/folio.py:22-23`)
- Guests restricted to their own orders (`services/orders.py:289-290`)
- Complaint packet access restricted to reporter for Guest/Service Staff roles (`services/complaints.py:79-80`)
- Cross-org access tested (`API_tests/test_api_coverage_matrix.py:294-315`)

### Function-Level Authorization
**Conclusion: Pass**

- Ratings enforce mutual guest/staff validation with order association checks (`services/ratings.py:40-71`)
- Self-rating blocked (`services/ratings.py:36-37`)
- Super-admin required for cross-organization scope on night audit/day-close (`api/routers/operations.py:42-53`)

### Tenant / User Data Isolation
**Conclusion: Pass**

- All queries filter by `organization_id` from the authenticated user
- Multi-org tested with `seabreeze` and `summit` organizations
- Cross-org folio access blocked and tested (`API_tests/test_api_coverage_matrix.py:294-315`)
- Cross-org complaint packet access blocked and tested (`API_tests/test_api_coverage_matrix.py:294-315`)
- Cross-org credit scoring blocked (`services/credit_score.py:41`)

### Admin / Internal / Debug Endpoint Protection
**Conclusion: Pass**

- `/health` endpoint is the only unprotected route - returns only status, no sensitive data (`backend/app/main.py:103-105`)
- Audit logs restricted to General Manager (`api/routers/governance.py:57`)
- No debug endpoints, no admin backdoors
- Demo seeding blocked in non-dev environments (`core/runtime_guard.py:27`)

---

## 7. Tests and Logging Review

### Unit Tests
**Conclusion: Pass**

6 unit test files covering:
- Order state machine transitions (valid and invalid) - `unit_tests/test_order_state_machine.py`
- Order compensation/rollback on failure - `unit_tests/test_order_compensation.py`
- Password policy enforcement - `unit_tests/test_auth_security_policy.py`
- Account lockout mechanism - `unit_tests/test_auth_security_policy.py`
- Night audit balanced/imbalanced folio detection - `unit_tests/test_night_audit_service.py`
- Credit score formula, clamping, invalid rating - `unit_tests/test_credit_score_service.py`
- GM dashboard metric keys and org scoping - `unit_tests/test_analytics_service.py`
- Sensitive data not in auth logs - `unit_tests/test_logging_sensitive_data.py`

### API / Integration Tests
**Conclusion: Pass**

6 API test files using `TestClient` with full database reset per test:
- `test_security_and_workflows_api.py`: Auth, quote confirmation, order lifecycle, lockout, session expiry, content approval roles, complaint roles, folio split permission mapping, refund adjustment entries, cookie-based auth
- `test_api_coverage_matrix.py`: Order catalog, transitions, folio CRUD, content releases with tag filtering, exports, governance endpoints, day-close, cross-org blocking, complaint windows, ratings (mutual/self/role), pagination, service durations
- `test_night_audit_api.py`: Night audit imbalance detection
- `test_health_and_credit_score_api.py`: Health check, credit score calculation, field-level masking for non-finance roles
- `test_analytics_api.py`: GM dashboard, org scoping, analytics snapshot with provenance binding enforcement
- `test_postgres_smoke.py`: PostgreSQL connectivity (conditional)

### Frontend Tests
5 test files:
- `frontend/src/router/index.test.js`
- `frontend/src/api/client.test.js`
- `frontend/src/components/LoginPanel.test.js`
- `frontend/src/components/LiveDataPanel.test.js`
- `frontend/src/components/OrderComposer.test.js`
- `frontend/src/composables/useOrderQuoteFlow.test.js`
- `frontend/src/App.integration.test.js`

2 E2E Playwright specs:
- `frontend/e2e/auth-security.spec.js`: Route protection, lockout enforcement, idle logout
- `frontend/e2e/business-flows.spec.js`: Guest order workflow, front desk reversal and print

### Logging Categories / Observability
**Conclusion: Pass**

- Structured logging with category/event format: `category=%s event=%s` (`core/logging.py:19`)
- Categories used: `auth`, `authz`, `finance`, `export`, `scheduler`
- Events cover: login success/failure, lockout, session expiry, order charges, folio operations, day-close, exports
- Audit events persisted to database with actor, action, resource type, resource ID, organization, and metadata

### Sensitive-Data Leakage Risk
**Conclusion: Pass**

- Passwords never logged - verified by `unit_tests/test_logging_sensitive_data.py`
- Tokens stored as SHA-256 hashes, never raw (`services/auth.py:31`)
- Field-level masking applied to notes for non-privileged roles (`services/masking.py`)
- Masking verified in API test (`test_health_and_credit_score_api.py:28-48`)
- Session cookie is httpOnly (not accessible to client JS)
- CSRF cookie is non-httpOnly by design (frontend needs to read it)

---

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview

| Aspect | Detail |
|---|---|
| Unit tests exist | Yes - 6 files in `unit_tests/` |
| API integration tests exist | Yes - 6 files in `API_tests/` |
| Frontend unit tests exist | Yes - 7 files |
| E2E tests exist | Yes - 2 Playwright specs |
| Test framework (backend) | pytest |
| Test framework (frontend) | vitest + Playwright |
| Test entry points | `python -m pytest unit_tests API_tests`, `npm run test`, `npm run test:e2e` |
| Test commands documented | Yes - `README.md:111-147` |
| Test fixture strategy | SQLite in-memory for unit tests, app-level DB reset for API tests |

### 8.2 Coverage Mapping Table

| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion | Coverage | Gap | Min Test Addition |
|---|---|---|---|---|---|
| Order state machine (valid transitions) | `test_order_state_machine.py:29-38` | State changes correctly | Sufficient | - | - |
| Order state machine (invalid transitions) | `test_order_state_machine.py:47-50` | ValueError raised | Sufficient | - | - |
| Quote re-confirmation (10 min) | `test_security_and_workflows_api.py:129-151` | Stale confirmation rejected 409 | Sufficient | - | - |
| Quote hash mismatch detection | `test_security_and_workflows_api.py:93-126` | Tampered cart rejected 409 | Sufficient | - | - |
| Packaging fee $2.50 enforcement | `test_api_coverage_matrix.py:30-63` | Quote w/ $2.50 passes | Basically covered | No test for wrong fee rejection | Test packaging_fee != 2.50 returns error |
| Order compensation on failure | `test_order_compensation.py:20-95` | Compensating FolioEntry created | Sufficient | - | - |
| Folio charge/payment/reversal | `test_api_coverage_matrix.py:91-148` | 200 status on each | Sufficient | - | - |
| Folio split (balance validation) | `test_api_coverage_matrix.py:116-131` | Bad split = 409, valid split = 200 | Sufficient | - | - |
| Folio merge | `test_api_coverage_matrix.py:133-139` | 200 on merge | Sufficient | - | - |
| Payment method enum constraint | `test_security_and_workflows_api.py:189-197` | Invalid method = 422 | Sufficient | - | - |
| Content approval workflow | `test_security_and_workflows_api.py:200-209` | Editor 403, GM 200 | Sufficient | - | - |
| Content tag-targeted release | `test_api_coverage_matrix.py:201-237` | VIP tag filtering, readership increment | Sufficient | - | - |
| Content rollback | `test_api_coverage_matrix.py:182-199` | Rollback returns 200 | Sufficient | - | - |
| Complaint 7-day window | `test_api_coverage_matrix.py:574-594` | 409 after 8 days | Sufficient | - | - |
| Complaint PDF packet export | `test_security_and_workflows_api.py:257-265` | 64-char checksum returned | Sufficient | - | - |
| Mutual ratings (guest/staff) | `test_api_coverage_matrix.py:376-441` | Guest->staff OK, staff->guest OK, self blocked | Sufficient | - | - |
| Credit score calculation | `test_credit_score_service.py:8-19` | Formula, clamping, invalid rating | Sufficient | - | - |
| Credit score field masking | `test_health_and_credit_score_api.py:28-48` | Finance sees full, desk sees masked | Sufficient | - | - |
| Night audit $0.01 tolerance | `test_night_audit_service.py:16-44` | Balanced passes, imbalanced fails | Sufficient | - | - |
| Day-close idempotency | `test_api_coverage_matrix.py:540-550` | Second run has `already_ran` flag | Sufficient | - | - |
| Authentication (401) | `test_security_and_workflows_api.py:66-68` | No token = 401 | Sufficient | - | - |
| Account lockout | `test_security_and_workflows_api.py:286-299`, `test_auth_security_policy.py:25-48` | locked_until set after 5 failures, Retry-After header | Sufficient | - | - |
| Session idle timeout (15 min) | `test_security_and_workflows_api.py:325-336` | Expired session = 401 "timed out" | Sufficient | - | - |
| Cross-org isolation (403) | `test_api_coverage_matrix.py:294-315` | Cross-org folio/complaint = 403 | Sufficient | - | - |
| Role-based access (403) | Multiple tests across all files | Various role restrictions verified | Sufficient | - | - |
| Pagination/filtering | `test_api_coverage_matrix.py:464-484` | Limit, offset, empty page, bad limit | Sufficient | - | - |
| Order dimension split/merge | `test_api_coverage_matrix.py:345-373` | Split 2 rows, merge to 1, missing = 404 | Sufficient | - | - |
| Export path traversal | `test_api_coverage_matrix.py:252-259` | `../../../../pwned` returns 400 | Sufficient | - | - |
| Sensitive data in logs | `test_logging_sensitive_data.py:19-44` | Password/Bearer not in log output | Sufficient | - | - |
| Password policy | `test_auth_security_policy.py:17-22` | Weak password rejected | Basically covered | Only tests one weak case | - |
| Analytics provenance binding | `test_analytics_api.py:31-84` | Missing metric = 409, bound = 200 | Sufficient | - | - |
| Cross-org release targeting | `test_api_coverage_matrix.py:262-291` | Hidden before approval, visible after | Sufficient | - | - |
| Governance endpoints | `test_api_coverage_matrix.py:487-537` | Metrics, datasets, lineage, dictionary | Sufficient | - | - |
| CSRF protection | None | - | Missing | No test for CSRF enforcement | Add test verifying POST without CSRF token returns 403 |
| Cookie-based auth flow | `test_security_and_workflows_api.py:275-283` | Cookie set, /me works | Sufficient | - | - |

### 8.3 Security Coverage Audit

| Security Area | Coverage | Assessment |
|---|---|---|
| Authentication | Sufficient | Login success, failure, lockout, unknown user, session persistence, cookie auth all tested |
| Route authorization | Sufficient | Multiple 403 tests across roles for folios, content, complaints, orders, day-close |
| Object-level authorization | Sufficient | Cross-org folio, complaint packet, and release access tested |
| Tenant / data isolation | Sufficient | Two organizations with cross-org blocking verified; GM dashboard org-scoping tested |
| Admin / internal protection | Basically covered | No admin/debug endpoints exist; audit logs restricted to GM (tested) |
| CSRF | Missing | CSRF middleware exists but no test verifies it. Combined with Issue #2, this is a significant gap |

### 8.4 Final Coverage Judgment

**Conclusion: Partial Pass**

**Covered**: Core business flows (orders, folios, content, complaints, ratings, credit scoring, night audit, day-close, governance, analytics), authentication, authorization (route and object level), data isolation, session management, sensitive data protection, pagination, error handling.

**Uncovered risks that could mask defects**: CSRF enforcement is not tested and appears broken in the frontend client (Issue #2). The packaging fee rejection path (wrong fee amount) is not explicitly tested. The day-close auto-scheduler thread is untestable statically.

---

## 9. Final Notes

This is a materially complete, well-engineered delivery that implements the vast majority of the prompt requirements with real business logic, not mocks. The architecture is clean, the test suite is meaningful, and security boundaries are properly enforced.

The most significant issue is **Issue #2 (High)**: the frontend API client does not send CSRF tokens, which would block all mutating operations when using the default cookie-based auth flow. This is a functional blocker for the primary browser-based workflow, though the bearer token auth mode (used by tests and the `x-harborsuite-auth-mode: bearer` header) would bypass the CSRF check since no session cookie is involved.

All other issues are Medium or Low severity. The project demonstrates professional software practice with audit trails, structured logging, configuration management, environment-aware security guards, and comprehensive test coverage of core business flows.
