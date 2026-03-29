from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.models import Base, Folio, FolioEntry, FolioEntryType, Order, Organization, PaymentMethod, Role, UserAccount
from backend.services import orders as orders_service


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_order_failure_adds_compensating_folio_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _db()
    org = Organization(name="Org", code="org")
    db.add(org)
    db.flush()
    guest = UserAccount(
        organization_id=org.id,
        username="guest@org.local",
        full_name="Guest",
        role=Role.GUEST,
        audience_tags="all",
        password_hash="pbkdf2_sha256$1$salt$hash",
    )
    db.add(guest)
    db.flush()
    folio = Folio(
        organization_id=org.id,
        guest_user_id=guest.id,
        guest_name="Guest",
        room_number="1201",
    )
    db.add(folio)
    db.commit()
    db.refresh(guest)
    db.refresh(folio)

    real_audit_event = orders_service.audit_event

    def _failing_audit(db_session, user, action, resource_type, resource_id, metadata):
        if action == "order_created":
            raise RuntimeError("forced-failure")
        return real_audit_event(db_session, user, action, resource_type, resource_id, metadata)

    monkeypatch.setattr(orders_service, "audit_event", _failing_audit)

    window_start = datetime.now(timezone.utc) + timedelta(minutes=5)
    window_end = datetime.now(timezone.utc) + timedelta(minutes=35)

    quote = orders_service.confirm_quote(
        db,
        guest,
        folio_id=folio.id,
        items=[{"name": "Tea", "quantity": 1, "unit_price": "5.00", "specs": {}}],
        payment_method=PaymentMethod.CASH,
        packaging_fee=Decimal("2.00"),
        service_fee=Decimal("1.00"),
        tax_rate=Decimal("0.10"),
        delivery_window_start=window_start,
        delivery_window_end=window_end,
    )

    with pytest.raises(ValueError, match="compensating folio entry"):
        orders_service.create_order(
            db,
            guest,
            folio_id=folio.id,
            items=[{"name": "Tea", "quantity": 1, "unit_price": "5.00", "specs": {}}],
            payment_method=PaymentMethod.CASH,
            packaging_fee=Decimal("2.00"),
            service_fee=Decimal("1.00"),
            tax_rate=Decimal("0.10"),
            order_note="note",
            delivery_window_start=window_start,
            delivery_window_end=window_end,
            price_confirmed_at=datetime.now(timezone.utc),
            reconfirm_token=quote.reconfirm_token,
        )

    orders = list(db.execute(select(Order)).scalars().all())
    assert orders == []

    adjustments = list(
        db.execute(select(FolioEntry).where(FolioEntry.folio_id == folio.id, FolioEntry.entry_type == FolioEntryType.ADJUSTMENT)).scalars().all()
    )
    assert adjustments
    assert "Compensating entry" in adjustments[-1].note
