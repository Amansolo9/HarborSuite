# Test Coverage Audit

## Project Type Detection
- Declared in `README.md`: `fullstack`.
- Inferred structure: `backend/` + `frontend/` (matches declaration).

## Backend Endpoint Inventory
Resolved route prefix: `/api/v1` (`backend/api/routes.py`), plus `GET /health` (`backend/app/main.py`).

1. `GET /health`
2. `POST /api/v1/auth/login`
3. `GET /api/v1/auth/me`
4. `POST /api/v1/auth/logout`
5. `GET /api/v1/operations/overview`
6. `POST /api/v1/credit-score/calculate`
7. `GET /api/v1/credit-score/{username}`
8. `POST /api/v1/night-audit/run`
9. `POST /api/v1/day-close/run`
10. `GET /api/v1/analytics/gm-dashboard`
11. `GET /api/v1/analytics/service-durations`
12. `POST /api/v1/analytics/snapshots`
13. `POST /api/v1/orders/confirm-quote`
14. `GET /api/v1/orders/catalog`
15. `POST /api/v1/orders`
16. `GET /api/v1/orders`
17. `POST /api/v1/orders/{order_id}/transition`
18. `POST /api/v1/orders/{order_id}/split`
19. `POST /api/v1/orders/{order_id}/merge`
20. `GET /api/v1/orders/{order_id}/allocations`
21. `GET /api/v1/folios`
22. `POST /api/v1/folios/{folio_id}/payments`
23. `POST /api/v1/folios/{folio_id}/charges`
24. `POST /api/v1/folios/{folio_id}/adjustments`
25. `POST /api/v1/folios/{folio_id}/reversals`
26. `POST /api/v1/folios/{folio_id}/split`
27. `GET /api/v1/folios/{folio_id}/splits`
28. `POST /api/v1/folios/merge`
29. `GET /api/v1/folios/{folio_id}/receipt`
30. `GET /api/v1/folios/{folio_id}/invoice`
31. `POST /api/v1/folios/{folio_id}/print`
32. `POST /api/v1/folios/{folio_id}/print-invoice`
33. `POST /api/v1/content/releases`
34. `GET /api/v1/content/releases`
35. `POST /api/v1/content/releases/{release_id}/approve`
36. `POST /api/v1/content/releases/{release_id}/rollback`
37. `POST /api/v1/complaints`
38. `GET /api/v1/complaints/{complaint_id}/packet`
39. `GET /api/v1/complaints/{complaint_id}/packet/download`
40. `POST /api/v1/ratings`
41. `GET /api/v1/ratings/me`
42. `POST /api/v1/exports`
43. `GET /api/v1/audit/logs`
44. `POST /api/v1/governance/metrics`
45. `POST /api/v1/governance/datasets`
46. `POST /api/v1/governance/lineage`
47. `GET /api/v1/governance/lineage`
48. `GET /api/v1/governance/dictionary/export`

## API Test Mapping Table
| Endpoint | Covered | Test Type | Test Files | Evidence |
|---|---|---|---|---|
| `GET /health` | yes | true no-mock HTTP | `API_tests/test_health_and_credit_score_api.py`, `API_tests/test_live_server_e2e.py` | `test_health_endpoint`, `test_health_endpoint_over_real_network` |
| `POST /api/v1/auth/login` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_postgres_smoke.py`, `API_tests/test_live_server_e2e.py` | `test_logout_revokes_session_and_clears_cookie`, `test_postgres_smoke_login_and_overview`, `test_full_login_and_authenticated_call_over_real_network` |
| `GET /api/v1/auth/me` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py`, `API_tests/test_security_and_workflows_api.py`, `API_tests/test_live_server_e2e.py` | `test_auth_me_and_overview`, `test_cookie_session_authentication_for_me_endpoint`, `test_full_login_and_authenticated_call_over_real_network` |
| `POST /api/v1/auth/logout` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py` | `test_logout_revokes_session_and_clears_cookie` |
| `GET /api/v1/operations/overview` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py`, `API_tests/test_postgres_smoke.py` | `test_auth_me_and_overview`, `test_postgres_smoke_login_and_overview` |
| `POST /api/v1/credit-score/calculate` | yes | true no-mock HTTP | `API_tests/test_health_and_credit_score_api.py` | `test_credit_score_endpoint` |
| `GET /api/v1/credit-score/{username}` | yes | true no-mock HTTP | `API_tests/test_health_and_credit_score_api.py` | `test_credit_score_endpoint`, `test_credit_profile_notes_are_masked_for_front_desk` |
| `POST /api/v1/night-audit/run` | yes | true no-mock HTTP | `API_tests/test_night_audit_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_night_audit_endpoint_reports_imbalanced_folios`, `test_cross_org_close_override_requires_super_admin` |
| `POST /api/v1/day-close/run` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_day_close_run_with_role_guard_and_idempotence` |
| `GET /api/v1/analytics/gm-dashboard` | yes | true no-mock HTTP | `API_tests/test_analytics_api.py` | `test_gm_dashboard_endpoint` |
| `GET /api/v1/analytics/service-durations` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_service_duration_metrics_endpoint` |
| `POST /api/v1/analytics/snapshots` | yes | true no-mock HTTP | `API_tests/test_analytics_api.py` | `test_analytics_snapshot_requires_and_persists_provenance_binding` |
| `POST /api/v1/orders/confirm-quote` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_quote_confirmation_required_for_order_submission` |
| `GET /api/v1/orders/catalog` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_order_catalog_endpoint_returns_runtime_catalog` |
| `POST /api/v1/orders` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_quote_confirmation_required_for_order_submission`, `_create_order` helper |
| `GET /api/v1/orders` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py`, `API_tests/test_live_server_e2e.py` | `test_protected_routes_require_authentication`, `test_list_pagination_and_filters` |
| `POST /api/v1/orders/{order_id}/transition` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_order_requires_recent_confirmation_and_reversal_reason`, `test_order_dimension_split_merge_and_list_with_failures` |
| `POST /api/v1/orders/{order_id}/split` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_order_dimension_split_merge_and_list_with_failures` |
| `POST /api/v1/orders/{order_id}/merge` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_order_dimension_split_merge_and_list_with_failures` |
| `GET /api/v1/orders/{order_id}/allocations` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_order_dimension_split_merge_and_list_with_failures` |
| `GET /api/v1/folios` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py` | `test_folios_list_endpoint_returns_org_scoped_rows` |
| `POST /api/v1/folios/{folio_id}/payments` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py` | `test_payment_method_is_enum_constrained` |
| `POST /api/v1/folios/{folio_id}/charges` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_manual_charge_requires_reason_and_roles` |
| `POST /api/v1/folios/{folio_id}/adjustments` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/folios/{folio_id}/reversals` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/folios/{folio_id}/split` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py`, `API_tests/test_security_and_workflows_api.py` | `test_folio_adjustment_split_merge_and_receipt_paths`, `test_folio_split_cross_org_returns_403` |
| `GET /api/v1/folios/{folio_id}/splits` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/folios/merge` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `GET /api/v1/folios/{folio_id}/receipt` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths`, `test_cross_org_object_access_is_blocked` |
| `GET /api/v1/folios/{folio_id}/invoice` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/folios/{folio_id}/print` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/folios/{folio_id}/print-invoice` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_folio_adjustment_split_merge_and_receipt_paths` |
| `POST /api/v1/content/releases` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_content_release_create_and_rollback` |
| `GET /api/v1/content/releases` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_content_tag_filter_and_readership_increment` |
| `POST /api/v1/content/releases/{release_id}/approve` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_content_approval_requires_general_manager_role` |
| `POST /api/v1/content/releases/{release_id}/rollback` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_content_release_create_and_rollback` |
| `POST /api/v1/complaints` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_complaint_role_matrix_and_audit_visibility`, `test_complaint_window_enforcement` |
| `GET /api/v1/complaints/{complaint_id}/packet` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_complaint_role_matrix_and_audit_visibility` |
| `GET /api/v1/complaints/{complaint_id}/packet/download` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_complaint_packet_download_returns_file` |
| `POST /api/v1/ratings` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_ratings_mutual_and_invalid_self` |
| `GET /api/v1/ratings/me` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_ratings_mutual_and_invalid_self` |
| `POST /api/v1/exports` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_export_creates_payload_file` |
| `GET /api/v1/audit/logs` | yes | true no-mock HTTP | `API_tests/test_security_and_workflows_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_complaint_role_matrix_and_audit_visibility` |
| `POST /api/v1/governance/metrics` | yes | true no-mock HTTP | `API_tests/test_analytics_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_analytics_snapshot_requires_and_persists_provenance_binding` |
| `POST /api/v1/governance/datasets` | yes | true no-mock HTTP | `API_tests/test_analytics_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_governance_endpoints_and_lineage_404` |
| `POST /api/v1/governance/lineage` | yes | true no-mock HTTP | `API_tests/test_analytics_api.py`, `API_tests/test_api_coverage_matrix.py` | `test_governance_endpoints_and_lineage_404` |
| `GET /api/v1/governance/lineage` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_governance_endpoints_and_lineage_404` |
| `GET /api/v1/governance/dictionary/export` | yes | true no-mock HTTP | `API_tests/test_api_coverage_matrix.py` | `test_governance_endpoints_and_lineage_404` |

## API Test Classification
1. True No-Mock HTTP
- `API_tests/test_health_and_credit_score_api.py`
- `API_tests/test_analytics_api.py`
- `API_tests/test_night_audit_api.py`
- `API_tests/test_api_coverage_matrix.py`
- `API_tests/test_security_and_workflows_api.py`
- `API_tests/test_postgres_smoke.py`
- `API_tests/test_live_server_e2e.py`

2. HTTP with Mocking
- None found in API tests.

3. Non-HTTP (unit/integration without HTTP)
- `unit_tests/*.py`

## Mock Detection Rules Results
- API tests: no `monkeypatch`/mocking on API execution path detected.
- Unit tests:
  - `unit_tests/test_order_compensation.py::test_order_failure_adds_compensating_folio_entry`
  - Mocked object: `orders_service.audit_event` via `monkeypatch.setattr`.
- Frontend tests include mocked `fetch` (`vi.stubGlobal`) in `frontend/src/App.integration.test.js`, `frontend/src/api/client.test.js`, `frontend/src/router/index.test.js`.

## Coverage Summary
- Total endpoints: `48`
- Endpoints with HTTP tests: `48`
- Endpoints with TRUE no-mock tests: `48`
- HTTP coverage: `100%`
- True API coverage: `100%`

## Unit Test Summary
### Backend Unit Tests
Test files:
- `unit_tests/test_auth_security_policy.py`
- `unit_tests/test_credit_score_service.py`
- `unit_tests/test_order_state_machine.py`
- `unit_tests/test_night_audit_service.py`
- `unit_tests/test_analytics_service.py`
- `unit_tests/test_logging_sensitive_data.py`
- `unit_tests/test_order_compensation.py`

Modules covered:
- Services: auth, credit score, analytics, night audit, orders
- Model/domain transition logic
- Security/password policy and log hygiene

Important backend modules not directly unit-tested:
- Router/controller units in `backend/api/routers/*.py`
- Governance, export, complaint packet internals as isolated units
- CSRF middleware as isolated unit

### Frontend Unit Tests (STRICT REQUIREMENT)
Frontend unit test files:
- `frontend/src/App.integration.test.js`
- `frontend/src/api/client.test.js`
- `frontend/src/router/index.test.js`
- `frontend/src/components/OrderComposer.test.js`
- `frontend/src/components/LoginPanel.test.js`
- `frontend/src/components/LiveDataPanel.test.js`
- `frontend/src/composables/useOrderQuoteFlow.test.js`

Frameworks/tools detected:
- Vitest
- Vue Test Utils
- jsdom environment

Components/modules covered:
- `App.vue`, `api/client.js`, `router/index.js`
- `LoginPanel.vue`, `OrderComposer.vue`, `LiveDataPanel.vue`
- `useOrderQuoteFlow.js`

Important frontend components/modules not tested:
- Major panels/composables including `FolioOperationsPanel.vue`, `FinanceClosePanel.vue`, `GovernanceOpsPanel.vue`, `CreditPanel.vue`, `ComplaintPanel.vue`, `OrderOperationsPanel.vue`, `RatingsPanel.vue`, `ServiceDurationPanel.vue`, `useDashboardData.js`, `useFolioOps.js`, `useOrderOps.js`, `useRoleAccess.js`, `useSessionLifecycle.js`.

Mandatory verdict:
- **Frontend unit tests: PRESENT**

Strict failure rule outcome:
- Not triggered (frontend unit tests are present).

### Cross-Layer Observation
- Backend and frontend both have tests.
- Coverage depth remains backend-heavy versus frontend breadth.

## API Observability Check
- Strong: most tests show explicit method/path, request payload, and status/body checks.
- Weak pockets: a subset asserts status/minimal keys only.

## Test Quality & Sufficiency
- Success/failure/edge/validation/auth/permission cases: strong overall.
- Real API execution: strong, including live network test (`API_tests/test_live_server_e2e.py`).
- Over-mocking: low for API tests.
- `run_tests.sh`: **FLAG** for strict environment portability because it still performs local `pip install` when `alembic` is missing.

## End-to-End Expectations
- Fullstack FE?BE E2E exists (`frontend/e2e/*.spec.js` with Playwright).
- Combined with 100% API endpoint coverage, expectation is substantially met.

## Test Coverage Score (0–100)
- **91/100**

## Score Rationale
- Full endpoint coverage with true no-mock API tests.
- Real network smoke path present.
- Deductions for frontend unit breadth gaps and `run_tests.sh` local-install branch.

## Key Gaps
- Frontend unit breadth on many core components/composables.
- `run_tests.sh` includes local dependency-install path.

## Confidence & Assumptions
- Confidence: high.
- Static inspection only; no tests/apps/scripts executed.

---

# README Audit

## High Priority Issues
- None.

## Medium Priority Issues
- README states Docker-only reviewer path, but references `run_tests.sh` behavior that can use host Python path; this is informationally mixed, though commands shown remain Docker-first.

## Low Priority Issues
- None material.

## Hard Gate Failures
- None.

## Hard Gate Evaluation (Evidence)
- Formatting: PASS (`README.md` is structured markdown).
- Startup instructions (fullstack): PASS (`docker compose up --build` at top).
- Access method: PASS (backend/frontend URLs + DB port listed).
- Verification method: PASS (explicit curl checks + expected outputs + UI flow).
- Environment rules: PASS (no `npm install`/`pip install`/`apt-get` commands present in README).
- Demo credentials (auth exists): PASS (all roles + usernames + password listed explicitly).

## Engineering Quality
- Tech stack, security posture, operational flow, and acceptance verification are clear.

## README Verdict (PASS / PARTIAL PASS / FAIL)
- **PASS**
