from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from API_tests.conftest import auth_headers
from backend.core.database import SessionLocal
from backend.models import Folio, Order


def _folio_for_guest(guest_name: str) -> Folio:
    with SessionLocal() as db:
        return db.execute(select(Folio).where(Folio.guest_name == guest_name)).scalar_one()


def _create_same_org_folio() -> str:
    with SessionLocal() as db:
        ref = db.execute(select(Folio).where(Folio.guest_name == "Maya Chen").order_by(Folio.opened_at.asc())).scalars().first()
        assert ref is not None
        folio = Folio(organization_id=ref.organization_id, guest_name="Walk-in Guest", room_number="1902")
        db.add(folio)
        db.commit()
        db.refresh(folio)
        return folio.id


def _create_order(client: TestClient) -> str:
    folio_id = _folio_for_guest("Maya Chen").id
    headers = auth_headers(client, "guest@seabreeze.local")
    start = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat()
    quote = client.post(
        "/api/v1/orders/confirm-quote",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Soup", "quantity": 1, "unit_price": "12.00", "size": "regular", "specs": {"salt": "low"}}],
            "payment_method": "cash",
            "tax_rate": "0.10",
            "delivery_window_start": start,
            "delivery_window_end": end,
        },
    )
    assert quote.status_code == 200
    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Soup", "quantity": 1, "unit_price": "12.00", "size": "regular", "specs": {"salt": "low"}}],
            "payment_method": "cash",
            "tax_rate": "0.10",
            "delivery_window_start": start,
            "delivery_window_end": end,
            "price_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reconfirm_token": quote.json()["reconfirm_token"],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_auth_me_and_overview(client: TestClient) -> None:
    headers = auth_headers(client, "desk@seabreeze.local")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["organization_name"]
    assert client.get("/api/v1/operations/overview", headers=headers).status_code == 200


def test_order_catalog_endpoint_returns_runtime_catalog(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    response = client.get("/api/v1/orders/catalog", headers=guest)
    assert response.status_code == 200
    rows = response.json()
    assert rows
    assert any(row["sku"] == "food_club_sandwich" for row in rows)


def test_order_transition_allows_created_to_in_prep(client: TestClient) -> None:
    order_id = _create_order(client)
    desk = auth_headers(client, "desk@seabreeze.local")
    response = client.post(f"/api/v1/orders/{order_id}/transition", headers=desk, json={"next_state": "in_prep"})
    assert response.status_code == 200
    assert response.json()["state"] == "in_prep"


def test_folio_adjustment_split_merge_and_receipt_paths(client: TestClient) -> None:
    folio = _folio_for_guest("Maya Chen")
    finance = auth_headers(client, "finance@seabreeze.local")
    guest = auth_headers(client, "guest@seabreeze.local")

    forbidden_adjustment = client.post(
        f"/api/v1/folios/{folio.id}/adjustments",
        headers=guest,
        json={"amount": "10.00", "reason": "No access"},
    )
    assert forbidden_adjustment.status_code == 403

    assert client.post(
        f"/api/v1/folios/{folio.id}/adjustments",
        headers=finance,
        json={"amount": "5.00", "reason": "Manual reconciliation entry"},
    ).status_code == 200

    reversal = client.post(
        f"/api/v1/folios/{folio.id}/reversals",
        headers=auth_headers(client, "desk@seabreeze.local"),
        json={"amount": "3.00", "reason": "Desk correction"},
    )
    assert reversal.status_code == 200

    bad_split = client.post(
        f"/api/v1/folios/{folio.id}/split",
        headers=finance,
        json={"allocations": ["1.00", "2.00"]},
    )
    assert bad_split.status_code == 409

    split = client.post(
        f"/api/v1/folios/{folio.id}/split",
        headers=finance,
        json={"allocations": ["20.00", "20.00"]},
    )
    assert split.status_code == 200
    split_rows = client.get(f"/api/v1/folios/{folio.id}/splits", headers=finance)
    assert split_rows.status_code == 200
    assert len(split_rows.json()) >= 2

    second_folio_id = _create_same_org_folio()
    merged = client.post(
        "/api/v1/folios/merge",
        headers=finance,
        json={"primary_folio_id": folio.id, "secondary_folio_id": second_folio_id},
    )
    assert merged.status_code == 200

    receipt = client.get(f"/api/v1/folios/{folio.id}/receipt", headers=finance)
    assert receipt.status_code == 200
    invoice = client.get(f"/api/v1/folios/{folio.id}/invoice", headers=finance)
    assert invoice.status_code == 200
    print_job = client.post(f"/api/v1/folios/{folio.id}/print", headers=auth_headers(client, "desk@seabreeze.local"))
    assert print_job.status_code == 200
    invoice_print_job = client.post(f"/api/v1/folios/{folio.id}/print-invoice", headers=auth_headers(client, "desk@seabreeze.local"))
    assert invoice_print_job.status_code == 200
    missing_receipt = client.get("/api/v1/folios/not-real/receipt", headers=finance)
    assert missing_receipt.status_code == 404


def test_folio_manual_charge_requires_reason_and_roles(client: TestClient) -> None:
    folio = _folio_for_guest("Maya Chen")
    desk = auth_headers(client, "desk@seabreeze.local")
    finance = auth_headers(client, "finance@seabreeze.local")
    guest = auth_headers(client, "guest@seabreeze.local")

    forbidden = client.post(
        f"/api/v1/folios/{folio.id}/charges",
        headers=guest,
        json={"amount": "12.00", "reason": "Manual minibar charge", "payment_method": "direct_bill"},
    )
    assert forbidden.status_code == 403

    short_reason = client.post(
        f"/api/v1/folios/{folio.id}/charges",
        headers=desk,
        json={"amount": "12.00", "reason": "bad", "payment_method": "direct_bill"},
    )
    assert short_reason.status_code == 422

    ok = client.post(
        f"/api/v1/folios/{folio.id}/charges",
        headers=finance,
        json={"amount": "12.00", "reason": "Manual minibar charge", "payment_method": "direct_bill"},
    )
    assert ok.status_code == 200
    assert any("Manual charge" in line for line in ok.json()["printable_lines"])


def test_content_release_create_and_rollback(client: TestClient) -> None:
    editor = auth_headers(client, "editor@seabreeze.local")
    created = client.post(
        "/api/v1/content/releases",
        headers=editor,
        json={
            "title": "Pool hours update",
            "body": "Pool closes at 21:30 for maintenance sweep.",
            "target_roles": ["guest"],
            "target_tags": ["all"],
        },
    )
    assert created.status_code == 200
    release_id = created.json()["id"]

    rollback = client.post(f"/api/v1/content/releases/{release_id}/rollback", headers=editor)
    assert rollback.status_code == 200


def test_content_tag_filter_and_readership_increment(client: TestClient) -> None:
    editor = auth_headers(client, "editor@seabreeze.local")
    gm = auth_headers(client, "gm@seabreeze.local")
    create = client.post(
        "/api/v1/content/releases",
        headers=editor,
        json={
            "title": "VIP Night Offer",
            "body": "VIP-only lounge access update.",
            "content_type": "announcement",
            "target_roles": ["guest"],
            "target_tags": ["vip"],
            "target_organizations": ["all"],
        },
    )
    assert create.status_code == 200
    release_id = create.json()["id"]

    guest = auth_headers(client, "guest@seabreeze.local")
    pre_approval = client.get("/api/v1/content/releases", headers=guest)
    assert pre_approval.status_code == 200
    assert all(row["id"] != release_id for row in pre_approval.json())

    approved = client.post(f"/api/v1/content/releases/{release_id}/approve", headers=gm)
    assert approved.status_code == 200

    first = client.get("/api/v1/content/releases", headers=guest)
    assert first.status_code == 200
    release = next((row for row in first.json() if row["title"] == "VIP Night Offer"), None)
    assert release is not None
    assert release["content_type"] == "announcement"
    first_count = release["readership_count"]

    second = client.get("/api/v1/content/releases", headers=guest)
    release2 = next((row for row in second.json() if row["title"] == "VIP Night Offer"), None)
    assert release2 is not None
    assert release2["readership_count"] == first_count


def test_export_creates_payload_file(client: TestClient) -> None:
    finance = auth_headers(client, "finance@seabreeze.local")
    created = client.post(
        "/api/v1/exports",
        headers=finance,
        json={"export_type": "nightly-close", "scope": "org"},
    )
    assert created.status_code == 200
    path = Path("data") / created.json()["storage_path"]
    assert path.exists()


def test_export_rejects_path_traversal_type(client: TestClient) -> None:
    finance = auth_headers(client, "finance@seabreeze.local")
    created = client.post(
        "/api/v1/exports",
        headers=finance,
        json={"export_type": "../../../../pwned", "scope": "org"},
    )
    assert created.status_code == 400


def test_cross_org_targeted_release_visible_after_approval(client: TestClient) -> None:
    editor = auth_headers(client, "editor@seabreeze.local")
    gm = auth_headers(client, "gm@seabreeze.local")
    summit_guest = auth_headers(client, "guest@summit.local")

    create = client.post(
        "/api/v1/content/releases",
        headers=editor,
        json={
            "title": "Summit conference notice",
            "body": "Conference ballroom opens at 07:00.",
            "content_type": "news",
            "target_roles": ["guest"],
            "target_tags": ["all"],
            "target_organizations": ["summit"],
        },
    )
    assert create.status_code == 200
    release_id = create.json()["id"]

    hidden_before = client.get("/api/v1/content/releases", headers=summit_guest)
    assert hidden_before.status_code == 200
    assert all(row["id"] != release_id for row in hidden_before.json())

    approved = client.post(f"/api/v1/content/releases/{release_id}/approve", headers=gm)
    assert approved.status_code == 200

    visible_after = client.get("/api/v1/content/releases", headers=summit_guest)
    assert visible_after.status_code == 200
    assert any(row["id"] == release_id for row in visible_after.json())


def test_cross_org_object_access_is_blocked(client: TestClient) -> None:
    seabreeze_guest = auth_headers(client, "guest@seabreeze.local")
    summit_gm = auth_headers(client, "gm@summit.local")
    folio_id = _folio_for_guest("Maya Chen").id

    cross_receipt = client.get(f"/api/v1/folios/{folio_id}/receipt", headers=summit_gm)
    assert cross_receipt.status_code == 403

    complaint = client.post(
        "/api/v1/complaints",
        headers=seabreeze_guest,
        json={
            "folio_id": folio_id,
            "subject": "Cross-org scope test",
            "detail": "Cross-organization packet access should fail.",
            "service_rating": 2,
            "violation_flag": False,
        },
    )
    assert complaint.status_code == 200
    packet = client.get(f"/api/v1/complaints/{complaint.json()['id']}/packet", headers=summit_gm)
    assert packet.status_code == 403


def test_complaint_packet_same_org_is_role_restricted(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    desk = auth_headers(client, "desk@seabreeze.local")
    finance = auth_headers(client, "finance@seabreeze.local")
    folio_id = _folio_for_guest("Maya Chen").id

    complaint = client.post(
        "/api/v1/complaints",
        headers=guest,
        json={
            "folio_id": folio_id,
            "subject": "Packet role scope test",
            "detail": "Desk users should not access arbitrary complaint packets.",
            "service_rating": 2,
            "violation_flag": False,
        },
    )
    assert complaint.status_code == 200
    complaint_id = complaint.json()["id"]

    denied = client.get(f"/api/v1/complaints/{complaint_id}/packet", headers=desk)
    assert denied.status_code == 403

    allowed = client.get(f"/api/v1/complaints/{complaint_id}/packet", headers=finance)
    assert allowed.status_code == 200


def test_order_dimension_split_merge_and_list_with_failures(client: TestClient) -> None:
    order_id = _create_order(client)
    desk = auth_headers(client, "desk@seabreeze.local")

    split = client.post(
        f"/api/v1/orders/{order_id}/split",
        headers=desk,
        json={
            "allocations": [
                {"supplier": "S1", "warehouse": "W1", "sla_tier": "gold", "quantity": 2},
                {"supplier": "S2", "warehouse": "W2", "sla_tier": "silver", "quantity": 1},
            ]
        },
    )
    assert split.status_code == 200
    listed = client.get(f"/api/v1/orders/{order_id}/allocations", headers=desk)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    merged = client.post(
        f"/api/v1/orders/{order_id}/merge",
        headers=desk,
        json={"supplier": "Merged", "warehouse": "WH", "sla_tier": "standard"},
    )
    assert merged.status_code == 200
    assert len(merged.json()) == 1

    missing = client.get("/api/v1/orders/missing/allocations", headers=desk)
    assert missing.status_code == 404


def test_ratings_mutual_and_invalid_self(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    desk = auth_headers(client, "desk@seabreeze.local")
    service = auth_headers(client, "service@seabreeze.local")
    unassigned_order_id = _create_order(client)

    guest_to_staff = client.post(
        "/api/v1/ratings",
        headers=guest,
        json={"to_username": "desk@seabreeze.local", "score": 4, "comment": "Helpful", "order_id": unassigned_order_id},
    )
    assert guest_to_staff.status_code == 409

    for state in ["confirmed", "in_prep", "delivered"]:
        assert client.post(f"/api/v1/orders/{unassigned_order_id}/transition", headers=desk, json={"next_state": state}).status_code == 200

    guest_to_staff = client.post(
        "/api/v1/ratings",
        headers=guest,
        json={"to_username": "desk@seabreeze.local", "score": 4, "comment": "Helpful", "order_id": unassigned_order_id},
    )
    assert guest_to_staff.status_code == 403

    staff_to_guest = client.post(
        "/api/v1/ratings",
        headers=service,
        json={"to_username": "guest@seabreeze.local", "score": 5, "comment": "Respectful guest", "order_id": unassigned_order_id},
    )
    assert staff_to_guest.status_code == 403

    assigned_order_id = _create_order(client)
    assert client.post(f"/api/v1/orders/{assigned_order_id}/transition", headers=desk, json={"next_state": "confirmed"}).status_code == 200
    assert client.post(f"/api/v1/orders/{assigned_order_id}/transition", headers=service, json={"next_state": "in_prep"}).status_code == 200
    assert client.post(f"/api/v1/orders/{assigned_order_id}/transition", headers=service, json={"next_state": "delivered"}).status_code == 200

    guest_to_service = client.post(
        "/api/v1/ratings",
        headers=guest,
        json={"to_username": "service@seabreeze.local", "score": 5, "comment": "Great delivery", "order_id": assigned_order_id},
    )
    assert guest_to_service.status_code == 200

    staff_to_guest = client.post(
        "/api/v1/ratings",
        headers=service,
        json={"to_username": "guest@seabreeze.local", "score": 5, "comment": "Respectful guest", "order_id": assigned_order_id},
    )
    assert staff_to_guest.status_code == 200

    desk_to_guest = client.post(
        "/api/v1/ratings",
        headers=desk,
        json={"to_username": "guest@seabreeze.local", "score": 5, "comment": "Respectful guest", "order_id": assigned_order_id},
    )
    assert desk_to_guest.status_code == 403

    self_rating = client.post(
        "/api/v1/ratings",
        headers=guest,
        json={"to_username": "guest@seabreeze.local", "score": 5, "order_id": assigned_order_id},
    )
    assert self_rating.status_code == 409

    mine = client.get("/api/v1/ratings/me", headers=guest)
    assert mine.status_code == 200
    assert len(mine.json()) >= 1


def test_order_rejects_missing_unit_price_as_validation_error(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    folio_id = _folio_for_guest("Maya Chen").id
    start = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

    quote = client.post(
        "/api/v1/orders/confirm-quote",
        headers=guest,
        json={
            "folio_id": folio_id,
            "items": [{"name": "Soup", "quantity": 1, "size": "regular", "specs": {"salt": "low"}}],
            "payment_method": "cash",
            "tax_rate": "0.10",
            "delivery_window_start": start,
            "delivery_window_end": end,
        },
    )
    assert quote.status_code == 422

def test_list_pagination_and_filters(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    gm = auth_headers(client, "gm@seabreeze.local")

    orders_limited = client.get("/api/v1/orders?limit=1&offset=0", headers=guest)
    assert orders_limited.status_code == 200
    assert len(orders_limited.json()) <= 1

    orders_empty_page = client.get("/api/v1/orders?limit=10&offset=999", headers=guest)
    assert orders_empty_page.status_code == 200
    assert orders_empty_page.json() == []

    bad_limit = client.get("/api/v1/orders?limit=9999", headers=guest)
    assert bad_limit.status_code == 422

    releases_filtered = client.get("/api/v1/content/releases?status=approved&limit=5&offset=0", headers=guest)
    assert releases_filtered.status_code == 200

    audit_empty_page = client.get("/api/v1/audit/logs?limit=10&offset=999", headers=gm)
    assert audit_empty_page.status_code == 200
    assert audit_empty_page.json() == []


def test_governance_endpoints_and_lineage_404(client: TestClient) -> None:
    gm = auth_headers(client, "gm@seabreeze.local")
    finance = auth_headers(client, "finance@seabreeze.local")

    metric = client.post(
        "/api/v1/governance/metrics",
        headers=gm,
        json={
            "metric_name": "occupancy_rate",
            "description": "Daily occupancy by sold rooms",
            "source_query_ref": "query://analytics/occupancy/v1",
            "version": 1,
        },
    )
    assert metric.status_code == 200

    dataset = client.post(
        "/api/v1/governance/datasets",
        headers=finance,
        json={"dataset_name": "folios_snapshot", "version": "v1", "dataset_schema": {"folio_id": "string", "balance": "decimal"}},
    )
    assert dataset.status_code == 200

    bad_lineage = client.post(
        "/api/v1/governance/lineage",
        headers=finance,
        json={
            "metric_name": "occupancy_rate",
            "dataset_version_id": "missing",
            "source_tables": ["folios"],
            "source_query_ref": "query://analytics/occupancy/v1",
        },
    )
    assert bad_lineage.status_code == 404

    lineage = client.post(
        "/api/v1/governance/lineage",
        headers=finance,
        json={
            "metric_name": "occupancy_rate",
            "dataset_version_id": dataset.json()["id"],
            "source_tables": ["folios", "orders"],
            "source_query_ref": "query://analytics/occupancy/v1",
        },
    )
    assert lineage.status_code == 200

    assert client.get("/api/v1/governance/lineage", headers=finance).status_code == 200
    dictionary = client.get("/api/v1/governance/dictionary/export", headers=finance)
    assert dictionary.status_code == 200
    assert len(dictionary.json()["fields"]) >= 1


def test_day_close_run_with_role_guard_and_idempotence(client: TestClient) -> None:
    guest = auth_headers(client, "guest@seabreeze.local")
    forbidden = client.post("/api/v1/day-close/run", headers=guest, json={})
    assert forbidden.status_code == 403

    finance = auth_headers(client, "finance@seabreeze.local")
    first = client.post("/api/v1/day-close/run", headers=finance, json={})
    assert first.status_code == 200
    second = client.post("/api/v1/day-close/run", headers=finance, json={})
    assert second.status_code == 200
    assert any(run["already_ran"] for run in second.json()["runs"])


def test_cross_org_close_override_requires_super_admin(client: TestClient) -> None:
    finance = auth_headers(client, "finance@seabreeze.local")
    day_close = client.post("/api/v1/day-close/run", headers=finance, json={"all_organizations": True})
    assert day_close.status_code == 403

    night_audit = client.post("/api/v1/night-audit/run", headers=finance, json={"all_organizations": True})
    assert night_audit.status_code == 403


def test_service_duration_metrics_endpoint(client: TestClient) -> None:
    order_id = _create_order(client)
    desk = auth_headers(client, "desk@seabreeze.local")
    for state in ["confirmed", "in_prep", "delivered"]:
        assert client.post(f"/api/v1/orders/{order_id}/transition", headers=desk, json={"next_state": state}).status_code == 200

    service = auth_headers(client, "service@seabreeze.local")
    response = client.get("/api/v1/analytics/service-durations", headers=service)
    assert response.status_code == 200
    assert "metrics" in response.json()


def test_complaint_window_enforcement(client: TestClient) -> None:
    folio = _folio_for_guest("Maya Chen")
    with SessionLocal() as db:
        order = db.execute(select(Order).where(Order.folio_id == folio.id)).scalars().first()
        assert order is not None
        order.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        db.commit()

    guest = auth_headers(client, "guest@seabreeze.local")
    response = client.post(
        "/api/v1/complaints",
        headers=guest,
        json={
            "folio_id": folio.id,
            "subject": "Window policy test",
            "detail": "Testing complaint window enforcement after 7 days.",
            "service_rating": 2,
            "violation_flag": False,
        },
    )
    assert response.status_code == 409
