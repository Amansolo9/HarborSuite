# HarborSuite Offline Hotel Commerce & PMS - Delivery Acceptance & Architecture Audit

---

## 1. Verdict

**Overall Conclusion: Partial Pass**

The project delivers a materially complete, well-structured full-stack implementation of the offline hotel PMS system described in the prompt. The backend covers all six roles, order state machine, folio management, content governance, complaints with PDF export, credit scoring, night audit, day-close, analytics, and data governance. The frontend is a real Vue.js SPA with role-based access, session management, and quote-reconfirm flow. Tests cover core happy paths, security boundaries, and critical business rules. However, several material gaps remain: the `shell=True` command injection risk in the printer service, the lack of CSRF protection for cookie-based auth, incomplete order-note 250-char enforcement on the backend, and missing folio merge permission for Front Desk (prompt requires it but route restricts to Finance only). These prevent a full pass.

---

## 2. Scope and Static Verification Boundary

### What Was Reviewed
- All Python backend source files (~20 modules), schemas, models, services, routers, config, security, logging
- All Vue.js frontend source files (~30 components/composables), router, API client, styles
- All unit tests (7 files), API integration tests (6 files), E2E tests (2 files)
- Docker configuration (Dockerfile referenced, docker-compose.yml, docker-compose.prod.yml)
- README.md, alembic config, seed data, order catalog

### What Was Not Reviewed
- `node_modules`, `__pycache__`, compiled assets, `.pytest_cache`
- Actual runtime behavior, container builds, database migrations at runtime
- `docker-compose.prod.yml` contents (referenced but not critical path)

### What Was Intentionally Not Executed
- No Docker builds, no `pytest`, no `npm test`, no `npm run build`, no Playwright
- No database connections, no API calls

### Claims Requiring Manual Verification
- Actual runtime startup and seeding
- Frontend visual rendering and interaction quality
- E2E test passage (Playwright requires running backend + frontend)
- Print command dispatch behavior
- Alembic migration execution

---

## 3. Repository / Requirement Mapping Summary

### Core Business Goal
Offline hotel PMS with on-property ordering, billing, content governance, complaints, ratings, credit scoring, night audit, day-close, analytics, and data governance -- all running without internet.

### Core Flows (from Prompt)
1. Guest browsing/ordering with multi-spec, packaging/service fees, 250-char notes, quote reconfirm within 10 min
2. Front Desk folio management: charge, reverse (with reason), split, merge, print
3. Content Editor: publish with approval workflow, targeted release, rollback, readership analytics
4. Mutual 1-5 star ratings, complaints within 7 days, credit score 300-850, PDF arbitration packets
5. Night audit at configurable time (default 3AM), blocks on $0.01 imbalance, reconciliation reports
6. State-machine orders (created->confirmed->in_prep->delivered->canceled->refunded), split/merge by supplier/warehouse/SLA, compensating entries
7. RBAC with 6 roles, 15-min session timeout, 10-char password policy, 5-attempt lockout, field-level masking
8. Data governance: metric definitions, lineage, dataset versions, data dictionary
9. PostgreSQL persistence, local file exports with checksums

### Implementation Mapping
| Requirement Area | Implementation Location |
|---|---|
| Order flow + state machine | `backend/services/orders.py`, `backend/models/models.py:71-78`, `backend/api/routers/orders.py` |
| Folio management | `backend/services/folio.py`, `backend/api/routers/folios.py` |
| Content governance | `backend/services/content.py`, `backend/api/routers/engagement.py` |
| Complaints + PDF packets | `backend/services/complaints.py`, `backend/api/routers/engagement.py` |
| Ratings | `backend/services/ratings.py`, `backend/api/routers/engagement.py` |
| Credit scoring | `backend/services/credit_score.py`, `backend/api/routers/operations.py` |
| Night audit | `backend/services/night_audit.py`, `backend/api/routers/operations.py` |
| Day-close | `backend/services/day_close.py`, `backend/api/routers/operations.py` |
| Analytics + dashboards | `backend/services/analytics.py`, `backend/api/routers/operations.py` |
| Data governance | `backend/services/governance.py`, `backend/api/routers/governance.py` |
| Auth + RBAC | `backend/services/auth.py`, `backend/core/security.py`, `backend/api/deps.py` |
| Frontend SPA | `frontend/src/App.vue`, components, composables, router |

---

## 4. Section-by-Section Review

### 4.1 Hard Gates

#### 4.1.1 Documentation and Static Verifiability
**Conclusion: Pass**

- `README.md` provides clear startup instructions for Docker (`docker compose up`) and local development (venv, pip install, uvicorn), frontend (`npm install && npm run dev`), and testing (`pytest`, `npm run test`, Playwright).
- Entry points are documented: `backend.app.main:app` at `README.md:62`, frontend at `localhost:5173`.
- Configuration via environment variables documented at `README.md:58-60`, `backend/core/config.py:45-67`.
- Test commands documented at `README.md:113-121`.
- Seed credentials documented at `README.md:150-155`.

#### 4.1.2 Material Deviation from Prompt
**Conclusion: Pass**

The implementation is centered on the hotel PMS business goal. All major areas from the prompt (ordering, folio, content, complaints, ratings, credit score, night audit, day-close, analytics, governance) are implemented. No major unrelated features are present. The project does not replace or weaken the core problem definition.

### 4.2 Delivery Completeness

#### 4.2.1 Coverage of Core Requirements
**Conclusion: Partial Pass**

Most core requirements are implemented. Gaps found:

| Requirement | Status | Evidence |
|---|---|---|
| Multi-spec selections (size, quantity, delivery window) | Implemented | `backend/schemas/pms.py:48-56` (OrderItemRequest with specs, size, quantity) |
| $2.50 packaging fee per food order | Partially implemented | Fee is configurable but not enforced at $2.50 -- `backend/schemas/pms.py:63` allows any value >= 0 |
| 18% optional service charge | Partially implemented | Same: configurable but not enforced at 18% |
| Order notes capped at 250 chars | Implemented | `backend/schemas/pms.py:65` `max_length=250` and `backend/models/models.py:162` `String(250)` |
| Quote reconfirm within 10 minutes | Implemented | `backend/services/orders.py:119-121`, `155-156` |
| Folio charge/reverse with required reason | Implemented | `backend/schemas/pms.py:159,164` `min_length=5` |
| Split/merge bills | Implemented | `backend/services/folio.py:114-183` |
| Print to local printers | Implemented | `backend/services/printer.py:14-24` |
| Payment methods (cash, card-present, gift cert, direct bill) | Implemented | `backend/models/models.py:25-30` |
| Content approval workflow + targeted release | Implemented | `backend/services/content.py:10-89` |
| Version rollback + readership analytics | Implemented | `backend/services/content.py:105-130`, readership at `content.py:74-86` |
| 1-5 star mutual ratings within 7 days | Ratings implemented; 7-day window is on complaints, not ratings | `backend/services/ratings.py:26`, `backend/services/complaints.py:40-41` |
| Credit score 300-850, default 700 | Implemented | `backend/services/credit_score.py:14-25`, `backend/models/models.py:378` |
| PDF arbitration packets | Implemented | `backend/services/complaints.py:60-70` using fpdf |
| State-machine orders | Implemented | `backend/models/models.py:71-78` |
| Split/merge orders by supplier/warehouse/SLA | Implemented | `backend/services/orders.py:324-403` |
| Compensating entries on exception | Implemented | `backend/services/orders.py:250-271` |
| Night audit at configurable time, $0.01 tolerance | Implemented | `backend/services/night_audit.py:25`, `backend/app/main.py:25-36` |
| Day-close auto-post room + tax | Implemented | `backend/services/day_close.py:73-90` |
| 15-min session timeout | Implemented | `backend/core/config.py:52`, `backend/services/auth.py:105` |
| 10-char password + complexity | Implemented | `backend/core/security.py:22-33` |
| 5-attempt lockout for 15 min | Implemented | `backend/services/auth.py:57-68` |
| Field-level masking | Implemented | `backend/services/masking.py:6-11` |
| Exports with checksums | Implemented | `backend/services/exports.py:21-23,57-59` |
| Data dictionary, metric defs, lineage, dataset versions | Implemented | `backend/services/governance.py`, `backend/models/models.py:297-343` |

**Gap**: The prompt says "Guests and Service Staff can rate each other 1-5 stars and file complaints within 7 days." The 7-day window is enforced on complaints (`complaints.py:40-41`) but there is no 7-day window check on ratings (`ratings.py` checks order completion state but not a time window). This is a partial gap.

#### 4.2.2 End-to-End Deliverable
**Conclusion: Pass**

- Complete project structure with backend (FastAPI), frontend (Vue.js), Docker, tests
- No mock/hardcoded behavior in place of real logic -- all services use SQLAlchemy ORM with real DB queries
- README provides documentation, seed data provides working demo state
- Not a code fragment or single-file example

### 4.3 Engineering and Architecture Quality

#### 4.3.1 Module Decomposition
**Conclusion: Pass**

- Clear separation: `backend/models/`, `backend/schemas/`, `backend/services/`, `backend/api/routers/`, `backend/core/`
- Frontend: `components/`, `composables/`, `views/`, `router/`, `api/`, `utils/`
- Services are domain-focused: `orders.py`, `folio.py`, `content.py`, `complaints.py`, `ratings.py`, `credit_score.py`, etc.
- No excessively large files -- largest service (`orders.py`) is ~404 lines, models at ~408 lines
- No redundant or unnecessary files observed

#### 4.3.2 Maintainability and Extensibility
**Conclusion: Pass**

- Order state machine uses enum-based transition map (`models.py:71-78`) -- extensible
- RBAC via `require_roles()` dependency injection (`deps.py:35-42`) -- clean pattern
- Configuration externalized via env vars (`config.py:45-67`)
- Catalog loaded from JSON file (`data/order_catalog.json`) -- runtime configurable
- Services use dependency injection for DB sessions
- Frontend composables properly decomposed for reuse

### 4.4 Engineering Details and Professionalism

#### 4.4.1 Error Handling, Logging, Validation
**Conclusion: Partial Pass**

**Strengths:**
- Structured logging with `log_event()` using `category=X event=Y` format (`logging.py:18-20`)
- Comprehensive audit trail via `audit_event()` on all state changes
- Pydantic validation on all request schemas with field constraints (`pms.py` throughout)
- Proper HTTP status code mapping: 401 for auth, 403 for authz, 404 for not found, 409 for conflicts, 422 for validation
- Runtime guard blocks insecure secrets in production (`runtime_guard.py:18-27`)

**Weaknesses:**
- `shell=True` in printer subprocess call (`printer.py:20`) -- command injection risk via `PRINT_COMMAND_TEMPLATE`
- Order compensation logic writes a compensating entry after rollback, but the compensating entry write itself could fail with no further fallback (`orders.py:252-271`)
- No rate limiting on API endpoints

#### 4.4.2 Product-Level Organization
**Conclusion: Pass**

- Docker Compose for deployment, production profile referenced
- Seed data for demo, blocked in production
- Cookie-based session auth (httpOnly), Bearer token support
- Environment-specific configuration
- Print queue with file-based fallback

### 4.5 Prompt Understanding and Requirement Fit

#### 4.5.1 Business Goal Implementation
**Conclusion: Pass**

The core business objective -- offline hotel commerce and PMS -- is correctly implemented. The system operates without internet dependency: PostgreSQL on-premise, local file exports, local print queue, no external API calls.

#### 4.5.2 Requirement Semantics
**Conclusion: Partial Pass**

- Minor semantic gap: prompt says "$2.50 packaging fee per food order plus an optional 18% service charge" -- implementation allows configurable amounts rather than enforcing these specific values. This is a reasonable design choice but worth noting.
- The "re-confirm within 10 minutes before the order is accepted" flow is correctly implemented with quote hash comparison.
- Folio merge route restricted to Finance only (`folios.py:175`) but prompt says "Front Desk Agents manage folios with ... split or merge bills." Front Desk should also be able to merge.

### 4.6 Aesthetics

#### 4.6.1 Visual and Interaction Design
**Conclusion: Cannot Confirm Statistically (requires runtime)**

**Static evidence of reasonable design:**
- Custom CSS design system in `app-shell.css` with CSS variables for colors, consistent border-radius, shadow system
- Responsive breakpoints at 1080px, 880px, 640px (`app-shell.css:73-86`)
- Consistent panel/card design language (`.panel`, `.stat-card`, `.table-card`)
- Form grid layout with labeled inputs
- Success/error message styling (`.message.success`, `.message.error`)
- Stats grid with 6 KPI cards
- Button states: `.primary-button` (deep teal), `.ghost-button` (outline), `:disabled` via binding
- Login panel with clear credential listing and password policy hint
- Warm neutral color palette (cream/teal/gold) appropriate for hospitality theme
- No Tailwind utility-class chaos -- clean semantic CSS

**Cannot confirm**: actual rendering, visual consistency of images/icons, hover/transition states, font rendering.

---

## 5. Issues / Suggestions (Severity-Rated)

### Issue 1: Command Injection via Print Template
**Severity: High**
**Title**: `shell=True` subprocess with user-influenced template path
**Evidence**: `backend/services/printer.py:20`
**Conclusion**: The `_dispatch_to_local_printer` function uses `subprocess.run(command, shell=True)`. While `PRINT_COMMAND_TEMPLATE` is an environment variable (not directly user-controlled), the `{file}` placeholder includes user-organization ID in the path (`printer.py:44`). If an attacker can influence organization naming or file paths, shell metacharacters could be injected.
**Impact**: Potential command execution on the server.
**Minimum Fix**: Use `subprocess.run(shlex.split(command), shell=False)` or validate/escape the file path before interpolation. Better: use `subprocess.run([...], shell=False)` with explicit argument list.

### Issue 2: No CSRF Protection for Cookie-Based Authentication
**Severity: High**
**Title**: Cookie auth without CSRF token on state-changing endpoints
**Evidence**: `backend/app/main.py:62-68` (CORS config), `backend/api/deps.py:24` (cookie token extraction), `backend/api/routers/operations.py:57-78` (login sets httpOnly cookie)
**Conclusion**: The application uses httpOnly cookies for session management. All state-changing POST endpoints accept this cookie. There is no CSRF token mechanism. The CORS policy limits origins to `localhost:5173` and `127.0.0.1:5173`, which provides some protection in development but is not sufficient for production deployment where the hostname will differ.
**Impact**: Cross-site request forgery attacks could execute actions on behalf of authenticated users.
**Minimum Fix**: Add a CSRF token (e.g., double-submit cookie pattern or synchronizer token) on all state-changing endpoints when cookie auth is used.

### Issue 3: Folio Merge Restricted to Finance Only -- Prompt Requires Front Desk
**Severity: Medium**
**Title**: Front Desk cannot merge folios despite prompt requirement
**Evidence**: `backend/api/routers/folios.py:174` -- `require_roles(Role.FINANCE)` but prompt says "Front Desk Agents manage folios with ... split or merge bills for shared rooms"
**Conclusion**: The merge endpoint only allows Finance role, while the prompt explicitly assigns folio merge capability to Front Desk Agents.
**Impact**: Front Desk Agents cannot perform a required business function.
**Minimum Fix**: Change `require_roles(Role.FINANCE)` to `require_roles(Role.FRONT_DESK, Role.FINANCE)` at `folios.py:174`.

### Issue 4: No Time Window Enforcement on Ratings
**Severity: Medium**
**Title**: Ratings lack 7-day filing window
**Evidence**: `backend/services/ratings.py` -- no time check against order completion date. Complaints enforce 7-day window at `complaints.py:40-41`, but ratings do not.
**Conclusion**: The prompt states "Guests and Service Staff can rate each other 1-5 stars and file complaints within 7 days." The 7-day window should also apply to ratings.
**Impact**: Ratings can be submitted for arbitrarily old orders.
**Minimum Fix**: Add a time check in `submit_rating()` similar to the complaint window check.

### Issue 5: Folio Split Also Restricted to Finance Only
**Severity: Medium**
**Title**: Front Desk cannot split folios despite prompt requirement
**Evidence**: `backend/api/routers/folios.py:138` -- `require_roles(Role.FRONT_DESK, Role.FINANCE)` for split is correct. Actually upon re-reading: split at line 138 does include `FRONT_DESK`. Only merge at line 174 is wrong. This issue is a duplicate of Issue 3 -- retracted.

*Correction: Split correctly includes Front Desk. Only merge is affected (Issue 3).*

### Issue 5 (revised): Packaging Fee Not Enforced at $2.50
**Severity: Low**
**Title**: Prompt specifies $2.50 packaging fee but backend accepts any value
**Evidence**: `backend/schemas/pms.py:63` -- `packaging_fee: Decimal = Field(default=Decimal("0.00"), ge=0)`
**Conclusion**: The prompt says "a $2.50 packaging fee per food order." The implementation allows any non-negative value. This is arguably a reasonable design choice (configurable vs. hardcoded), but it means the specific $2.50 rule is not enforced server-side.
**Impact**: Clients could submit orders with incorrect packaging fees.
**Minimum Fix**: Either validate that packaging_fee equals $2.50 for food orders, or document this as an intentional configurability choice.

### Issue 6: Night Audit Does Not Block Day-Close on Imbalance > $0.01
**Severity: Medium**
**Title**: Day-close proceeds to close folios even when audit fails
**Evidence**: `backend/services/day_close.py:97-103` -- When `passed=False` (audit fails), the run status is `FAILED` and folios are NOT closed. This is actually correct behavior.
**Conclusion**: Upon re-reading, the day-close logic correctly blocks closure when audit fails (`day_close.py:97`: `if passed: ... close folios`, else status = FAILED). The prompt requirement is satisfied. **Retracted.**

### Issue 6 (revised): CORS Allow-Origins Hardcoded to Localhost
**Severity: Medium**
**Title**: CORS origins only allow localhost, production deployment will fail
**Evidence**: `backend/app/main.py:64` -- `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]`
**Conclusion**: In production or LAN deployment, the frontend will be served from a different hostname. The hardcoded localhost origins will block legitimate requests.
**Impact**: Frontend cannot communicate with backend in any non-localhost deployment.
**Minimum Fix**: Make CORS origins configurable via environment variable.

### Issue 7: Compensating Entry After Rollback May Fail Silently
**Severity: Low**
**Title**: If compensating folio entry write fails after order creation rollback, no further recovery
**Evidence**: `backend/services/orders.py:251-271` -- After `db.rollback()`, the code attempts to write a compensating entry and commit. If this second commit fails, the exception propagates but the compensation is lost.
**Impact**: In edge cases, a failed order could leave no compensating trace.
**Minimum Fix**: Wrap the compensating write in its own try/except with logging.

### Issue 8: Alembic Migration References Non-Existent Initial Migration
**Severity: Low**
**Title**: Single Alembic migration file present but bootstrap uses `create_all`
**Evidence**: `backend/alembic/versions/20260326_0001_initial.py` exists, but `backend/core/database.py` and `scripts/bootstrap_db.py` use `Base.metadata.create_all()` bypassing migrations.
**Impact**: In production, schema evolution would require manual migration management.
**Minimum Fix**: Document whether Alembic or create_all is the intended schema management path.

---

## 6. Security Review Summary

### Authentication Entry Points
**Conclusion: Pass**
- Single login endpoint: `POST /api/v1/auth/login` (`operations.py:56-89`)
- Cookie-based (httpOnly, secure in production) and Bearer token support
- Password hashing with PBKDF2-SHA256, 200k iterations (`security.py:36-41`)
- Constant-time comparison via `hmac.compare_digest` (`security.py:57`)
- Account lockout after 5 failures for 15 minutes (`auth.py:57-68`)
- Session tokens stored as SHA-256 hashes in DB (`auth.py:30-31`)

### Route-Level Authorization
**Conclusion: Pass**
- `require_roles()` dependency enforces role checks on every protected route (`deps.py:35-42`)
- All routes reviewed have appropriate role restrictions
- `get_current_user()` dependency on all authenticated endpoints
- 401 for missing/invalid tokens, 403 for insufficient roles

### Object-Level Authorization
**Conclusion: Pass**
- Organization-scoped access on all resource queries: `folio.py:18-24`, `orders.py:288-290`, `complaints.py:77-78`, `content.py:97-98`, `ratings.py:22-23`, `credit_score.py:41-42`, `governance.py:81`
- Guest can only access own folios (`folio.py:22-23`)
- Guest can only access own orders (`orders.py:280-282`)
- Complaint packet access restricted to reporter for guest/staff roles (`complaints.py:79-80`)
- Cross-org access blocked with explicit tests (`test_api_coverage_matrix.py:294-315`)

### Function-Level Authorization
**Conclusion: Pass**
- Role matrices enforced per function:
  - Orders: Guest + Front Desk can create; Front Desk + Service Staff + Finance can transition
  - Folios: Front Desk + Finance for charges/payments/reversals; Finance only for adjustments
  - Content: Content Editor creates; GM approves
  - Complaints: Guest + Service Staff file
  - Credit Score: Front Desk + Finance + GM
  - Night Audit / Day-Close: Finance + GM
  - Audit Logs: GM only
  - Governance: Finance + GM (except dictionary export includes Content Editor)

### Tenant / User Data Isolation
**Conclusion: Pass**
- Multi-organization model with `organization_id` on all core entities
- All service queries filter by `user.organization_id`
- Cross-org override requires super-admin usernames (`operations.py:38-53`)
- Two organizations seeded for testing cross-org isolation
- Tests explicitly verify cross-org blocking (`test_api_coverage_matrix.py:294-315`)

### Admin / Internal / Debug Endpoint Protection
**Conclusion: Pass**
- `/health` is the only unprotected endpoint (appropriate for health checks)
- No admin panels, debug endpoints, or internal APIs exposed
- Runtime guard blocks demo data in production (`runtime_guard.py:18-27`)
- Super-admin override audited (`operations.py:171-179`)

### Security Concern: `shell=True` in Printer
**Conclusion: High Risk (see Issue 1)**
- `printer.py:20` uses `shell=True` with template interpolation

### Security Concern: No CSRF Protection
**Conclusion: High Risk (see Issue 2)**
- Cookie-based auth without CSRF tokens on state-changing endpoints

---

## 7. Tests and Logging Review

### Unit Tests
**Conclusion: Pass**
- 7 unit test files covering: order state machine, auth/security policy, credit score service, sensitive data logging, night audit service, order compensation, analytics service
- Tests use in-memory SQLite for isolation
- Framework: pytest
- Key areas covered: state transitions (valid + invalid), password policy, account lockout, credit score formula + clamping, night audit balanced/imbalanced, compensating folio entries, GM dashboard metrics

### API / Integration Tests
**Conclusion: Pass**
- 6 API test files with `TestClient` from FastAPI
- Comprehensive coverage: auth flows, order lifecycle, folio operations, content governance, complaints, ratings, exports, governance, day-close, night audit, pagination, cross-org isolation
- Tests verify HTTP status codes, response payloads, and database state
- `conftest.py` resets DB between tests with `reset_db` fixture
- Notable tests: lockout + Retry-After header, session idle timeout, cross-org access blocking, complaint 7-day window, quote reconfirm hash validation

### E2E Tests (Playwright)
**Conclusion: Cannot Confirm Statistically**
- 2 E2E spec files: `auth-security.spec.js`, `business-flows.spec.js`
- `auth-security.spec.js` tests: unauthenticated redirect, lockout enforcement, idle session logout
- Cannot confirm execution without running Playwright against live backend

### Logging Categories / Observability
**Conclusion: Pass**
- Structured `log_event()` with category/event format (`logging.py:18-20`)
- Categories observed: `auth`, `authz`, `finance`, `export`, `scheduler`
- Events: login_success, login_failed, account_locked, session_expired, order_charge_posted, folio_payment_posted, etc.
- Audit events persisted to `audit_events` table with actor, action, resource, metadata

### Sensitive-Data Leakage Risk
**Conclusion: Pass**
- Dedicated test verifying passwords/tokens not in logs (`test_logging_sensitive_data.py:19-44`)
- Field-level masking for sensitive notes (`masking.py:6-11`)
- Masking applied in receipt/invoice building (`folio.py:189,205`) and credit profile (`credit_score.py:97`)
- Session tokens stored as SHA-256 hashes, not plaintext (`auth.py:30-31`)
- No password or token values in log_event calls (verified by inspection)

---

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview

| Dimension | Status |
|---|---|
| Unit tests exist | Yes -- 7 files in `unit_tests/` |
| API integration tests exist | Yes -- 6 files in `API_tests/` |
| E2E tests exist | Yes -- 2 files in `frontend/e2e/` |
| Frontend unit tests exist | Yes -- 4 files (`*.test.js`) |
| Test framework (backend) | pytest |
| Test framework (frontend) | vitest + Playwright |
| Test entry points | `python -m pytest unit_tests API_tests`, `npm run test`, `npm run test:e2e` |
| Documentation of test commands | `README.md:113-121` |

### 8.2 Coverage Mapping Table

| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion | Coverage | Gap | Min Test Addition |
|---|---|---|---|---|---|
| Order state machine transitions | `test_order_state_machine.py:29-50` | Valid/invalid transitions | Sufficient | -- | -- |
| Quote reconfirm + hash validation | `test_security_and_workflows_api.py:70-127` | 200 on match, 409 on tamper/reuse | Sufficient | -- | -- |
| 10-minute price confirmation expiry | `test_security_and_workflows_api.py:129-168` | 409 on stale confirmation | Sufficient | -- | -- |
| Order compensating entry on failure | `test_order_compensation.py:20-96` | No orders persisted, adjustment entry present | Sufficient | -- | -- |
| Account lockout after 5 failures | `test_auth_security_policy.py:25-48`, `test_security_and_workflows_api.py:286-299` | `locked_until` set, 401 + Retry-After | Sufficient | -- | -- |
| Password policy (10+ chars, complexity) | `test_auth_security_policy.py:17-22` | ValueError on weak password | Basically covered | Only tests one weak case | Add tests for edge cases (9 chars, missing digit, etc.) |
| Session idle timeout (15 min) | `test_security_and_workflows_api.py:325-336` | 401 after artificially aging `last_seen_at` | Sufficient | -- | -- |
| Cookie-based session auth | `test_security_and_workflows_api.py:275-283` | `set-cookie` present, `/auth/me` succeeds | Sufficient | -- | -- |
| Night audit $0.01 tolerance | `test_night_audit_service.py:17-44`, `test_night_audit_api.py:6-14` | Balanced passes, imbalanced fails | Sufficient | -- | -- |
| Day-close auto-post + idempotence | `test_api_coverage_matrix.py:540-550` | 200 on run, `already_ran` on repeat | Basically covered | No test for folio status change | Add assertion that folios are closed/failed |
| Credit score formula + clamping | `test_credit_score_service.py:8-20` | Score=710, clamp to 300, reject rating=0 | Sufficient | -- | -- |
| Folio split/merge | `test_api_coverage_matrix.py:91-148` | Split 200, bad split 409, merge 200 | Sufficient | -- | -- |
| Content approval workflow | `test_security_and_workflows_api.py:200-209`, `test_api_coverage_matrix.py:182-238` | Editor 403 on approve, GM 200, rollback 200, readership | Sufficient | -- | -- |
| Complaint 7-day window | `test_api_coverage_matrix.py:574-594` | 409 when order > 7 days old | Sufficient | -- | -- |
| Mutual ratings validation | `test_api_coverage_matrix.py:376-441` | Self-rating 409, unassigned staff 403, assigned staff 200, guest<->staff reciprocal | Sufficient | -- | -- |
| Cross-org object isolation | `test_api_coverage_matrix.py:294-315` | 403 on cross-org receipt/complaint packet | Sufficient | -- | -- |
| Cross-org close override requires super-admin | `test_api_coverage_matrix.py:553-559` | 403 for non-super-admin | Sufficient | -- | -- |
| Export with checksum + path traversal | `test_api_coverage_matrix.py:240-259` | File exists, 400 on traversal attempt | Sufficient | -- | -- |
| Protected routes require auth (401) | `test_security_and_workflows_api.py:66-68` | 401 on unauthenticated `/orders` | Basically covered | Only one route tested | Add 401 checks for more routes |
| Sensitive data not in logs | `test_logging_sensitive_data.py:19-44` | Password/Bearer not in caplog | Sufficient | -- | -- |
| Pagination and filtering | `test_api_coverage_matrix.py:464-484` | Limit/offset, 422 on bad limit, filter by status | Sufficient | -- | -- |
| Refund requires reversal reason | `test_security_and_workflows_api.py:180-186` | 409 when missing reason | Sufficient | -- | -- |
| Payment method enum validation | `test_security_and_workflows_api.py:189-197` | 422 on invalid enum value | Sufficient | -- | -- |
| Role-restricted complaint filing | `test_security_and_workflows_api.py:212-255` | Guest 200, Service 200, Desk 403 | Sufficient | -- | -- |
| GM dashboard analytics | `test_analytics_service.py:19-72` | All 7 metric keys returned | Basically covered | No API-level test | Add API test for `/analytics/gm-dashboard` |
| Governance lineage 404 | `test_api_coverage_matrix.py:487-537` | 404 on missing dataset, 200 on valid lineage | Sufficient | -- | -- |

### 8.3 Security Coverage Audit

| Security Area | Test Coverage | Could Severe Defects Remain Undetected? |
|---|---|---|
| Authentication | Covered: lockout, timeout, cookie auth, unknown user 401 | Low risk -- major auth paths tested |
| Route authorization | Covered: multiple role-restricted endpoints tested for 403 | Low risk -- consistent `require_roles` pattern |
| Object-level authorization | Covered: cross-org receipt 403, cross-org complaint packet 403, guest-only folio access | Low risk -- pattern is consistent across services |
| Tenant data isolation | Covered: explicit cross-org tests with two organizations | Low risk -- `organization_id` filter present on all queries |
| Admin/internal protection | Covered: super-admin override tested, no exposed debug endpoints | Low risk |
| CSRF | **Not tested** | **Yes -- CSRF attacks could succeed** |
| Command injection (printer) | **Not tested** | **Yes -- shell=True is untested for malicious input** |

### 8.4 Final Coverage Judgment

**Conclusion: Partial Pass**

**Covered major risks:**
- Authentication flows (lockout, timeout, cookie/bearer)
- Authorization (role-based, object-level, cross-org)
- Order lifecycle (state machine, quote reconfirm, compensation)
- Financial operations (folio CRUD, split/merge, night audit)
- Content governance (approval, rollback, targeted release)
- Data integrity (export checksums, path traversal prevention)

**Uncovered risks that mean tests could pass while severe defects remain:**
- No CSRF testing -- cookie-based auth vulnerable to cross-site request forgery
- No security testing of printer command injection vector
- No test for ratings time-window enforcement (because it's not implemented)
- Only one route tested for unauthenticated 401 (though consistent pattern reduces risk)

---

## 9. Final Notes

This is a materially complete, well-engineered delivery that covers the vast majority of the prompt's requirements. The backend architecture is clean with proper separation of concerns, consistent RBAC enforcement, comprehensive audit logging, and organization-scoped data isolation. The frontend provides a real multi-role SPA with session management, quote reconfirm flow, and role-based UI rendering.

The two highest-severity issues (shell injection in printer, lack of CSRF protection) are genuine security concerns that should be addressed before production deployment but do not indicate architectural negligence -- they are specific gaps in an otherwise security-conscious codebase. The folio merge permission gap (Issue 3) is a clear prompt-alignment bug with a one-line fix.

The test suite is notably thorough for a delivery of this scope, with explicit cross-organization isolation tests, quote hash tampering tests, and sensitive-data-in-logs verification. The main testing gap is the absence of CSRF and command injection security tests.
