from fastapi.testclient import TestClient

from API_tests.conftest import auth_headers


def test_gm_dashboard_endpoint(client: TestClient) -> None:
    headers = auth_headers(client, "gm@seabreeze.local")
    response = client.get("/api/v1/analytics/gm-dashboard", headers=headers)
    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "scale_index",
        "churn_rate",
        "participation_rate",
        "order_volume",
        "fund_income_expense",
        "budget_execution",
        "approval_efficiency",
    }


def test_gm_dashboard_is_organization_scoped(client: TestClient) -> None:
    seabreeze = auth_headers(client, "gm@seabreeze.local")
    summit = auth_headers(client, "gm@summit.local")
    sea = client.get("/api/v1/analytics/gm-dashboard", headers=seabreeze)
    sum_ = client.get("/api/v1/analytics/gm-dashboard", headers=summit)
    assert sea.status_code == 200
    assert sum_.status_code == 200
    assert sea.json()["order_volume"] != sum_.json()["order_volume"]


def test_analytics_snapshot_requires_and_persists_provenance_binding(client: TestClient) -> None:
    finance = auth_headers(client, "finance@seabreeze.local")
    gm = auth_headers(client, "gm@seabreeze.local")

    missing = client.post(
        "/api/v1/analytics/snapshots",
        headers=finance,
        json={"snapshot_type": "service_durations"},
    )
    assert missing.status_code == 409

    metric = client.post(
        "/api/v1/governance/metrics",
        headers=gm,
        json={
            "metric_name": "service_duration_metrics",
            "description": "Service duration provenance test metric",
            "source_query_ref": "query://analytics/service_duration/v1",
            "version": 1,
        },
    )
    assert metric.status_code == 200

    dataset = client.post(
        "/api/v1/governance/datasets",
        headers=finance,
        json={
            "dataset_name": "service_duration_snapshot",
            "version": "v1",
            "dataset_schema": {"order_id": "string", "duration_minutes": "decimal"},
        },
    )
    assert dataset.status_code == 200

    lineage = client.post(
        "/api/v1/governance/lineage",
        headers=finance,
        json={
            "metric_name": "service_duration_metrics",
            "dataset_version_id": dataset.json()["id"],
            "source_tables": ["orders"],
            "source_query_ref": "query://analytics/service_duration/v1",
        },
    )
    assert lineage.status_code == 200

    recorded = client.post(
        "/api/v1/analytics/snapshots",
        headers=finance,
        json={"snapshot_type": "service_durations"},
    )
    assert recorded.status_code == 200
    assert recorded.json()["status"] == "recorded"
    assert recorded.json()["provenance_bindings"] >= 1
