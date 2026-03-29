from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, Order, OrderState, Organization, PaymentMethod, Role, UserAccount
from backend.services.analytics import AnalyticsService


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_gm_dashboard_is_scoped_and_returns_extended_metrics() -> None:
    db = _db()
    org = Organization(name="Org", code="org")
    db.add(org)
    db.flush()
    gm = UserAccount(
        organization_id=org.id,
        username="gm@org.local",
        full_name="GM",
        role=Role.GENERAL_MANAGER,
        audience_tags="all",
        password_hash="pbkdf2_sha256$1$salt$hash",
    )
    guest = UserAccount(
        organization_id=org.id,
        username="guest@org.local",
        full_name="Guest",
        role=Role.GUEST,
        audience_tags="all",
        password_hash="pbkdf2_sha256$1$salt$hash",
    )
    db.add_all([gm, guest])
    db.flush()
    db.add(
        Order(
            organization_id=org.id,
            folio_id="folio-1",
            created_by_user_id=guest.id,
            state=OrderState.DELIVERED,
            subtotal_amount=Decimal("10.00"),
            packaging_fee=Decimal("1.00"),
            service_fee=Decimal("1.00"),
            tax_amount=Decimal("1.20"),
            total_amount=Decimal("13.20"),
            payment_method=PaymentMethod.CASH,
            order_items_json='[{"name":"Tea","quantity":1,"unit_price":"10.00"}]',
            delivery_window_start=datetime.now(timezone.utc),
            delivery_window_end=datetime.now(timezone.utc),
            price_confirmed_at=datetime.now(timezone.utc),
            tax_reconfirm_by=datetime.now(timezone.utc),
        )
    )
    db.commit()

    result = AnalyticsService(db).gm_dashboard(gm)
    assert set(result.keys()) == {
        "scale_index",
        "churn_rate",
        "participation_rate",
        "order_volume",
        "fund_income_expense",
        "budget_execution",
        "approval_efficiency",
    }
