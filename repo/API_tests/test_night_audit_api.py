from fastapi.testclient import TestClient

from API_tests.conftest import auth_headers


def test_night_audit_endpoint_reports_imbalanced_folios(client: TestClient) -> None:
    headers = auth_headers(client, "finance@seabreeze.local")
    response = client.post("/api/v1/night-audit/run", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_folios"] >= 1
    assert body["failed_count"] >= 1
    assert body["passed"] is False
    assert any(line["reason"].startswith("Out of balance") for line in body["results"])
