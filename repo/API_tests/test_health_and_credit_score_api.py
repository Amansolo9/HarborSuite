from fastapi.testclient import TestClient

from API_tests.conftest import auth_headers


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "offline-ready"}


def test_credit_score_endpoint(client: TestClient) -> None:
    headers = auth_headers(client, "finance@seabreeze.local")
    response = client.post(
        "/api/v1/credit-score/calculate",
        json={"username": "guest@seabreeze.local", "rating": 5, "penalties": [10, 15], "violation": True, "note": "late payment"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "guest@seabreeze.local"
    assert body["score"] == 685
    profile = client.get("/api/v1/credit-score/guest@seabreeze.local", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["violation_count"] >= 1


def test_credit_profile_notes_are_masked_for_front_desk(client: TestClient) -> None:
    finance_headers = auth_headers(client, "finance@seabreeze.local")
    desk_headers = auth_headers(client, "desk@seabreeze.local")

    create = client.post(
        "/api/v1/credit-score/calculate",
        json={"username": "guest@seabreeze.local", "rating": 4, "penalties": [5], "violation": False, "note": "medical accommodation details"},
        headers=finance_headers,
    )
    assert create.status_code == 200

    finance_profile = client.get("/api/v1/credit-score/guest@seabreeze.local", headers=finance_headers)
    desk_profile = client.get("/api/v1/credit-score/guest@seabreeze.local", headers=desk_headers)
    assert finance_profile.status_code == 200
    assert desk_profile.status_code == 200

    finance_note = finance_profile.json()["events"][0]["note"]
    desk_note = desk_profile.json()["events"][0]["note"]
    assert finance_note == "medical accommodation details"
    assert desk_note != finance_note
    assert "*" in desk_note
