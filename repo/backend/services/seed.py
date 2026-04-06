from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import hash_password
from backend.models import ContentRelease, ContentStatus, Folio, FolioEntry, FolioEntryType, Order, OrderState, Organization, PaymentMethod, Role, UserAccount


def _now() -> datetime:
    return datetime.now(timezone.utc)


def seed_if_empty(db: Session) -> None:
    if not settings.seed_demo_data:
        return

    if db.execute(select(Organization.id)).first() is not None:
        return

    org_one = Organization(name="Seabreeze Harbor Hotel", code="seabreeze")
    org_two = Organization(name="Summit Crest Lodge", code="summit")
    db.add_all([org_one, org_two])
    db.flush()

    default_password = hash_password("Harbor#2026!")
    users = [
        UserAccount(organization_id=org_one.id, username="guest@seabreeze.local", full_name="Maya Chen", role=Role.GUEST, audience_tags="vip,nightlife", password_hash=default_password),
        UserAccount(organization_id=org_one.id, username="desk@seabreeze.local", full_name="Iris Bell", role=Role.FRONT_DESK, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_one.id, username="service@seabreeze.local", full_name="Jon Park", role=Role.SERVICE_STAFF, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_one.id, username="finance@seabreeze.local", full_name="Noah Silva", role=Role.FINANCE, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_one.id, username="editor@seabreeze.local", full_name="Alma Stone", role=Role.CONTENT_EDITOR, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_one.id, username="gm@seabreeze.local", full_name="Priya Rao", role=Role.GENERAL_MANAGER, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_two.id, username="guest@summit.local", full_name="Tara Voss", role=Role.GUEST, audience_tags="all", password_hash=default_password),
        UserAccount(organization_id=org_two.id, username="gm@summit.local", full_name="Leif Moran", role=Role.GENERAL_MANAGER, audience_tags="all", password_hash=default_password),
    ]
    db.add_all(users)
    db.flush()

    primary_guest = next(user for user in users if user.username == "guest@seabreeze.local")
    summit_guest = next(user for user in users if user.username == "guest@summit.local")

    folio_one = Folio(organization_id=org_one.id, guest_user_id=primary_guest.id, guest_name=primary_guest.full_name, room_number="1208")
    folio_two = Folio(organization_id=org_two.id, guest_user_id=summit_guest.id, guest_name=summit_guest.full_name, room_number="305")
    db.add_all([folio_one, folio_two])
    db.flush()

    db.add_all(
        [
            FolioEntry(folio_id=folio_one.id, entry_type=FolioEntryType.CHARGE, amount=Decimal("128.00"), note="Welcome package"),
            FolioEntry(folio_id=folio_one.id, entry_type=FolioEntryType.PAYMENT, amount=Decimal("80.00"), payment_method=PaymentMethod.CARD_PRESENT_MANUAL, note="Pre-authorized deposit"),
            FolioEntry(folio_id=folio_two.id, entry_type=FolioEntryType.CHARGE, amount=Decimal("96.00"), note="Room service"),
        ]
    )

    db.add(
        Order(
            organization_id=org_one.id,
            folio_id=folio_one.id,
            created_by_user_id=primary_guest.id,
            state=OrderState.CONFIRMED,
            subtotal_amount=Decimal("22.00"),
            packaging_fee=Decimal("2.50"),
            service_fee=Decimal("3.96"),
            tax_amount=Decimal("2.85"),
            total_amount=Decimal("31.31"),
            payment_method=PaymentMethod.DIRECT_BILL,
            order_items_json=json.dumps(
                [
                    {
                        "name": "Late-night ramen",
                        "quantity": 1,
                        "unit_price": "22.00",
                        "size": "regular",
                        "specs": {"broth": "miso"},
                        "delivery_slot_label": "late-night",
                    }
                ]
            ),
            order_note="Late-night ramen",
            delivery_window_start=_now() + timedelta(minutes=15),
            delivery_window_end=_now() + timedelta(minutes=45),
            price_confirmed_at=_now(),
            tax_reconfirm_by=_now() + timedelta(minutes=10),
        )
    )

    db.add_all(
        [
            ContentRelease(
                organization_id=org_one.id,
                title="Rooftop jazz service update",
                body="Live set moves to lounge B after 21:00 because of wind advisory.",
                version=2,
                status=ContentStatus.PENDING_APPROVAL,
                target_roles="guest,front_desk",
                target_tags="vip,nightlife",
                readership_count=14,
            ),
            ContentRelease(
                organization_id=org_one.id,
                title="Breakfast terrace reopening",
                body="The terrace reopens at 06:30 with expanded allergy-safe stations.",
                version=1,
                status=ContentStatus.APPROVED,
                target_roles="guest",
                target_tags="all",
                readership_count=61,
            ),
        ]
    )
    db.commit()
