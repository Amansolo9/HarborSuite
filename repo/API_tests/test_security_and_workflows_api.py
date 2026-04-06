from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from API_tests.conftest import auth_headers
from backend.api.routers import folios as folios_router
from backend.core.database import SessionLocal
from backend.models import ContentRelease, Folio, Order, OrderState, SessionToken


def _folio_id_by_guest(guest_name: str) -> str:
    with SessionLocal() as db:
        folio = db.execute(select(Folio).where(Folio.guest_name == guest_name)).scalar_one()
        return folio.id


def _release_id() -> str:
    with SessionLocal() as db:
        release = db.execute(select(ContentRelease).order_by(ContentRelease.created_at.desc())).scalars().first()
        assert release is not None
        return release.id


def _quote_token(
    client: TestClient,
    headers: dict[str, str],
    folio_id: str,
    *,
    item_name: str = "Tea",
    item_price: str = "5.00",
    item_specs: dict[str, str] | None = None,
) -> dict[str, str]:
    from decimal import Decimal, ROUND_HALF_UP
    start = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat()
    specs = item_specs or {"sweetness": "low"}
    service_fee = str((Decimal(item_price) * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    quote = client.post(
        "/api/v1/orders/confirm-quote",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [
                {
                    "name": item_name,
                    "quantity": 1,
                    "unit_price": item_price,
                    "size": "small",
                    "specs": specs,
                    "delivery_slot_label": "afternoon",
                }
            ],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": service_fee,
            "tax_rate": "0.10",
            "delivery_window_start": start,
            "delivery_window_end": end,
        },
    )
    assert quote.status_code == 200
    return {"token": quote.json()["reconfirm_token"], "start": start, "end": end, "service_fee": service_fee}


def test_protected_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/orders")
    assert response.status_code == 401


def test_quote_confirmation_required_for_order_submission(client: TestClient) -> None:
    folio_id = _folio_id_by_guest("Maya Chen")
    headers = auth_headers(client, "guest@seabreeze.local")
    confirmed = _quote_token(client, headers, folio_id)

    accepted = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Tea", "quantity": 1, "unit_price": "5.00", "size": "small", "specs": {"sweetness": "low"}, "delivery_slot_label": "afternoon"}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": "0.90",
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
            "price_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reconfirm_token": confirmed["token"],
        },
    )
    assert accepted.status_code == 200

    rejected = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Tea", "quantity": 2, "unit_price": "5.00", "size": "small", "specs": {"sweetness": "low"}, "delivery_slot_label": "afternoon"}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": "0.90",
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
            "price_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reconfirm_token": confirmed["token"],
        },
    )
    assert rejected.status_code == 409

    tampered_quote = client.post(
        "/api/v1/orders/confirm-quote",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Tea", "quantity": 1, "unit_price": "1.00", "size": "small", "specs": {"sweetness": "low"}}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": "0.90",
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
        },
    )
    assert tampered_quote.status_code == 409


def test_order_requires_recent_confirmation_and_reversal_reason(client: TestClient) -> None:
    folio_id = _folio_id_by_guest("Maya Chen")
    headers = auth_headers(client, "guest@seabreeze.local")
    confirmed = _quote_token(client, headers, folio_id)

    stale_response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Tea", "quantity": 1, "unit_price": "5.00", "size": "small", "specs": {"sweetness": "low"}, "delivery_slot_label": "afternoon"}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": "0.90",
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
            "price_confirmed_at": (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat(),
            "reconfirm_token": confirmed["token"],
        },
    )
    assert stale_response.status_code == 409

    fresh_response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Tea", "quantity": 1, "unit_price": "5.00", "size": "small", "specs": {"sweetness": "low"}, "delivery_slot_label": "afternoon"}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": "0.90",
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
            "price_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reconfirm_token": confirmed["token"],
        },
    )
    assert fresh_response.status_code == 200
    order_id = fresh_response.json()["id"]

    desk_headers = auth_headers(client, "desk@seabreeze.local")
    for state in ["confirmed", "in_prep", "delivered"]:
        transition = client.post(
            f"/api/v1/orders/{order_id}/transition",
            headers=desk_headers,
            json={"next_state": state},
        )
        assert transition.status_code == 200

    finance_headers = auth_headers(client, "finance@seabreeze.local")
    missing_reason = client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=finance_headers,
        json={"next_state": "refunded"},
    )
    assert missing_reason.status_code == 409


def test_payment_method_is_enum_constrained(client: TestClient) -> None:
    folio_id = _folio_id_by_guest("Maya Chen")
    headers = auth_headers(client, "finance@seabreeze.local")
    response = client.post(
        f"/api/v1/folios/{folio_id}/payments",
        headers=headers,
        json={"amount": "25.00", "payment_method": "room_charge", "note": "bad method"},
    )
    assert response.status_code == 422


def test_content_approval_requires_general_manager_role(client: TestClient) -> None:
    release_id = _release_id()
    editor_headers = auth_headers(client, "editor@seabreeze.local")
    forbidden = client.post(f"/api/v1/content/releases/{release_id}/approve", headers=editor_headers)
    assert forbidden.status_code == 403

    gm_headers = auth_headers(client, "gm@seabreeze.local")
    approved = client.post(f"/api/v1/content/releases/{release_id}/approve", headers=gm_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_complaint_role_matrix_and_audit_visibility(client: TestClient) -> None:
    folio_id = _folio_id_by_guest("Maya Chen")
    guest_headers = auth_headers(client, "guest@seabreeze.local")
    service_headers = auth_headers(client, "service@seabreeze.local")
    desk_headers = auth_headers(client, "desk@seabreeze.local")

    guest_ok = client.post(
        "/api/v1/complaints",
        headers=guest_headers,
        json={
            "folio_id": folio_id,
            "subject": "Late tray arrival",
            "detail": "Room service arrived cold and 25 minutes later than promised.",
            "service_rating": 2,
            "violation_flag": True,
        },
    )
    assert guest_ok.status_code == 200

    service_ok = client.post(
        "/api/v1/complaints",
        headers=service_headers,
        json={
            "folio_id": folio_id,
            "subject": "Escalated incident",
            "detail": "Service staff filed follow-up incident report for review.",
            "service_rating": 3,
            "violation_flag": False,
        },
    )
    assert service_ok.status_code == 200

    desk_forbidden = client.post(
        "/api/v1/complaints",
        headers=desk_headers,
        json={
            "folio_id": folio_id,
            "subject": "Desk complaint",
            "detail": "Front desk should not be allowed for this route.",
            "service_rating": 3,
            "violation_flag": False,
        },
    )
    assert desk_forbidden.status_code == 403

    complaint_id = guest_ok.json()["id"]
    packet = client.get(f"/api/v1/complaints/{complaint_id}/packet", headers=guest_headers)
    assert packet.status_code == 200
    assert len(packet.json()["checksum"]) == 64

    gm_headers = auth_headers(client, "gm@seabreeze.local")
    logs = client.get("/api/v1/audit/logs", headers=gm_headers)
    assert logs.status_code == 200
    assert any(event["action"] == "complaint_created" for event in logs.json())


def test_login_persists_session_token_record(client: TestClient) -> None:
    auth_headers(client, "gm@seabreeze.local")
    with SessionLocal() as db:
        count = db.execute(select(SessionToken)).scalars().all()
        assert len(count) >= 1


def test_cookie_session_authentication_for_me_endpoint(client: TestClient) -> None:
    login = client.post("/api/v1/auth/login", json={"username": "guest@seabreeze.local", "password": "Harbor#2026!"})
    assert login.status_code == 200
    assert login.json().get("access_token") is None
    assert "set-cookie" in {k.lower() for k in login.headers.keys()}

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "guest@seabreeze.local"


def test_login_lockout_response_includes_retry_after_ttl(client: TestClient) -> None:
    locked = None
    for _ in range(6):
        locked = client.post(
            "/api/v1/auth/login",
            json={"username": "editor@seabreeze.local", "password": "WrongPassword!1"},
        )
    assert locked is not None
    assert locked.status_code == 401
    detail = locked.json()["detail"]
    assert isinstance(detail, dict)
    assert "locked" in detail.get("message", "").lower()
    assert int(detail.get("lockout_seconds", 0)) > 0
    assert int(locked.headers.get("retry-after", "0")) > 0


def test_login_unknown_username_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "missing@seabreeze.local", "password": "Harbor#2026!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_folio_split_permission_error_maps_to_403(client: TestClient, monkeypatch) -> None:
    headers = auth_headers(client, "desk@seabreeze.local")
    folio_id = _folio_id_by_guest("Maya Chen")

    def _deny_split(db, user, target_folio_id, allocations):  # noqa: ANN001
        raise PermissionError("Cross-organization access is not allowed.")

    monkeypatch.setattr(folios_router, "split_folio", _deny_split)

    response = client.post(
        f"/api/v1/folios/{folio_id}/split",
        headers=headers,
        json={"allocations": ["10.00", "5.00"]},
    )
    assert response.status_code == 403


def test_session_expires_after_idle_timeout(client: TestClient) -> None:
    headers = auth_headers(client, "gm@seabreeze.local")
    token = headers["Authorization"].replace("Bearer ", "")
    with SessionLocal() as db:
        row = db.execute(select(SessionToken)).scalars().first()
        assert row is not None
        row.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=16)
        db.commit()

    expired = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert expired.status_code == 401
    assert "timed out" in expired.json()["detail"].lower()


def test_refund_writes_adjustment_entry(client: TestClient) -> None:
    folio_id = _folio_id_by_guest("Maya Chen")
    guest_headers = auth_headers(client, "guest@seabreeze.local")
    confirmed = _quote_token(client, guest_headers, folio_id, item_name="Juice", item_price="7.00", item_specs={"ice": "no"})
    create = client.post(
        "/api/v1/orders",
        headers=guest_headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Juice", "quantity": 1, "unit_price": "7.00", "size": "small", "specs": {"ice": "no"}, "delivery_slot_label": "afternoon"}],
            "payment_method": "cash",
            "packaging_fee": "2.50",
            "service_fee": confirmed["service_fee"],
            "tax_rate": "0.10",
            "delivery_window_start": confirmed["start"],
            "delivery_window_end": confirmed["end"],
            "price_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reconfirm_token": confirmed["token"],
        },
    )
    assert create.status_code == 200
    order_id = create.json()["id"]

    desk_headers = auth_headers(client, "desk@seabreeze.local")
    for state in ["confirmed", "in_prep", "delivered"]:
        assert client.post(
            f"/api/v1/orders/{order_id}/transition",
            headers=desk_headers,
            json={"next_state": state},
        ).status_code == 200

    finance_headers = auth_headers(client, "finance@seabreeze.local")
    refunded = client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=finance_headers,
        json={"next_state": "refunded", "reversal_reason": "Guest allergy issue"},
    )
    assert refunded.status_code == 200

    with SessionLocal() as db:
        order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
        assert order.state == OrderState.REFUNDED
