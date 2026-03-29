from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging import get_logger, log_event
from backend.models import (
    ALLOWED_ORDER_TRANSITIONS,
    FolioEntry,
    FolioEntryType,
    Order,
    OrderAllocation,
    OrderQuote,
    OrderState,
    PaymentMethod,
    Role,
    UserAccount,
)
from backend.services.audit import audit_event
from backend.services.folio import get_folio_for_user

TWOPLACES = Decimal("0.01")
logger = get_logger(__name__)

CATALOG_PRICES: dict[str, tuple[str, Decimal]] = {
    "beverage_tea": ("Tea", Decimal("5.00")),
    "beverage_coffee": ("Coffee", Decimal("6.00")),
    "beverage_juice": ("Juice", Decimal("7.00")),
    "food_soup": ("Soup", Decimal("12.00")),
    "food_club_sandwich": ("Club sandwich", Decimal("14.00")),
    "spa_express_massage": ("Express massage add-on", Decimal("65.00")),
    "late_checkout_2pm": ("Late checkout extension", Decimal("45.00")),
    "amenity_welcome_basket": ("Welcome amenity basket", Decimal("32.00")),
}

NAME_TO_SKU: dict[str, str] = {
    "tea": "beverage_tea",
    "coffee": "beverage_coffee",
    "juice": "beverage_juice",
    "soup": "food_soup",
    "club sandwich": "food_club_sandwich",
    "express massage add-on": "spa_express_massage",
    "late checkout extension": "late_checkout_2pm",
    "welcome amenity basket": "amenity_welcome_basket",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _normalize_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in items:
        sku = str(item.get("sku") or NAME_TO_SKU.get(str(item.get("name", "")).strip().lower(), "")).strip()
        if not sku or sku not in CATALOG_PRICES:
            raise ValueError("Unknown catalog item. Submit a valid item SKU.")
        catalog_name, catalog_price = CATALOG_PRICES[sku]
        submitted_price_raw = item.get("unit_price")
        if submitted_price_raw is not None:
            submitted = _quantize(Decimal(str(submitted_price_raw)))
            if submitted != _quantize(catalog_price):
                raise ValueError("Submitted unit price does not match authoritative catalog pricing.")
        specs = item.get("specs") or {}
        if not isinstance(specs, dict):
            raise ValueError("Item specs must be an object map.")
        normalized.append(
            {
                "sku": sku,
                "name": catalog_name,
                "quantity": int(str(item["quantity"])),
                "unit_price": str(_quantize(catalog_price)),
                "size": str(item.get("size") or ""),
                "specs": {str(k): str(v) for k, v in sorted(specs.items())},
                "delivery_slot_label": str(item.get("delivery_slot_label") or ""),
            }
        )
    return normalized


def _quote_payload(
    *,
    folio_id: str,
    items: list[dict[str, object]],
    payment_method: PaymentMethod,
    packaging_fee: Decimal,
    service_fee: Decimal,
    tax_rate: Decimal,
    delivery_window_start: datetime,
    delivery_window_end: datetime,
) -> dict[str, object]:
    return {
        "folio_id": folio_id,
        "items": _normalize_items(items),
        "payment_method": payment_method.value,
        "packaging_fee": str(_quantize(packaging_fee)),
        "service_fee": str(_quantize(service_fee)),
        "tax_rate": str(_quantize(tax_rate)),
        "delivery_window_start": _as_utc(delivery_window_start).isoformat(),
        "delivery_window_end": _as_utc(delivery_window_end).isoformat(),
        "tax_rule_version": settings.order_tax_rule_version,
    }


def _quote_hash(payload: dict[str, object]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _validate_delivery_window(start: datetime, end: datetime) -> None:
    utc_start = _as_utc(start)
    utc_end = _as_utc(end)
    if utc_end <= utc_start:
        raise ValueError("Delivery window end must be after start.")
    if utc_end - utc_start > timedelta(hours=6):
        raise ValueError("Delivery window cannot exceed 6 hours.")


def _ensure_recent_confirmation(price_confirmed_at: datetime) -> None:
    if _now() - _as_utc(price_confirmed_at) > timedelta(minutes=10):
        raise ValueError("Price confirmation expired. Reconfirm cart totals within 10 minutes.")


def confirm_quote(
    db: Session,
    user: UserAccount,
    *,
    folio_id: str,
    items: list[dict[str, object]],
    payment_method: PaymentMethod,
    packaging_fee: Decimal,
    service_fee: Decimal,
    tax_rate: Decimal,
    delivery_window_start: datetime,
    delivery_window_end: datetime,
) -> OrderQuote:
    folio = get_folio_for_user(db, user, folio_id)
    _validate_delivery_window(delivery_window_start, delivery_window_end)
    payload = _quote_payload(
        folio_id=folio.id,
        items=items,
        payment_method=payment_method,
        packaging_fee=packaging_fee,
        service_fee=service_fee,
        tax_rate=tax_rate,
        delivery_window_start=delivery_window_start,
        delivery_window_end=delivery_window_end,
    )
    quote = OrderQuote(
        organization_id=user.organization_id,
        user_id=user.id,
        folio_id=folio.id,
        quote_hash=_quote_hash(payload),
        reconfirm_token=secrets.token_urlsafe(32),
        expires_at=_now() + timedelta(minutes=10),
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    audit_event(db, user, "order_quote_confirmed", "order_quote", quote.id, {"folio_id": folio.id})
    return quote


def _verify_quote(
    db: Session,
    user: UserAccount,
    reconfirm_token: str,
    payload: dict[str, object],
) -> None:
    quote = db.execute(select(OrderQuote).where(OrderQuote.reconfirm_token == reconfirm_token)).scalar_one_or_none()
    if quote is None:
        raise ValueError("Invalid quote reconfirm token.")
    if quote.organization_id != user.organization_id or quote.user_id != user.id:
        raise PermissionError("Quote token does not belong to this user.")
    if _now() > _as_utc(quote.expires_at):
        raise ValueError("Quote reconfirm token expired.")
    if quote.quote_hash != _quote_hash(payload):
        raise ValueError("Cart or tax rules changed since confirmation. Reconfirm quote.")


def create_order(
    db: Session,
    user: UserAccount,
    folio_id: str,
    items: list[dict[str, object]],
    payment_method: PaymentMethod,
    packaging_fee: Decimal,
    service_fee: Decimal,
    tax_rate: Decimal,
    order_note: str | None,
    delivery_window_start: datetime,
    delivery_window_end: datetime,
    price_confirmed_at: datetime,
    reconfirm_token: str,
) -> Order:
    folio = get_folio_for_user(db, user, folio_id)
    _validate_delivery_window(delivery_window_start, delivery_window_end)
    _ensure_recent_confirmation(price_confirmed_at)
    payload = _quote_payload(
        folio_id=folio.id,
        items=items,
        payment_method=payment_method,
        packaging_fee=packaging_fee,
        service_fee=service_fee,
        tax_rate=tax_rate,
        delivery_window_start=delivery_window_start,
        delivery_window_end=delivery_window_end,
    )
    _verify_quote(db, user, reconfirm_token, payload)

    subtotal = sum((Decimal(str(item["unit_price"])) * Decimal(int(str(item["quantity"]))) for item in items), Decimal("0.00"))
    tax_amount = _quantize((subtotal + packaging_fee + service_fee) * tax_rate)
    total = _quantize(subtotal + packaging_fee + service_fee + tax_amount)

    order = Order(
        organization_id=user.organization_id,
        folio_id=folio.id,
        created_by_user_id=user.id,
        state=OrderState.CREATED,
        subtotal_amount=_quantize(subtotal),
        packaging_fee=_quantize(packaging_fee),
        service_fee=_quantize(service_fee),
        tax_amount=tax_amount,
        total_amount=total,
        payment_method=payment_method,
        order_items_json=json.dumps(_normalize_items(items)),
        order_note=order_note,
        delivery_window_start=_as_utc(delivery_window_start),
        delivery_window_end=_as_utc(delivery_window_end),
        price_confirmed_at=_as_utc(price_confirmed_at),
        tax_reconfirm_by=_now() + timedelta(minutes=10),
    )
    try:
        db.add(order)
        db.flush()
        db.add(
            FolioEntry(
                folio_id=folio.id,
                entry_type=FolioEntryType.CHARGE,
                amount=total,
                payment_method=payment_method,
                note=f"Order {order.id[:8]} posted to room",
            )
        )
        audit_event(db, user, "order_created", "order", order.id, {"items": json.dumps(items), "total": str(total)})
        db.commit()
        log_event(logger, "finance", "order_charge_posted", order_id=order.id, total=str(total), method=payment_method.value)
        db.refresh(order)
        return order
    except Exception as exc:
        db.rollback()
        db.add(
            FolioEntry(
                folio_id=folio.id,
                entry_type=FolioEntryType.ADJUSTMENT,
                amount=total,
                payment_method=payment_method,
                note=f"Compensating entry: failed order create ({str(exc)[:120]})",
            )
        )
        audit_event(
            db,
            user,
            "order_create_compensated",
            "folio",
            folio.id,
            {"reason": str(exc)[:120], "amount": str(total)},
        )
        db.commit()
        log_event(logger, "finance", "order_create_compensated", folio_id=folio.id, amount=str(total), reason=str(exc)[:120])
        raise ValueError("Order processing failed. A compensating folio entry was posted.") from exc


def parse_order_items(order: Order) -> list[dict[str, object]]:
    return json.loads(order.order_items_json)


def list_orders(db: Session, user: UserAccount) -> list[Order]:
    q = select(Order).where(Order.organization_id == user.organization_id)
    if user.role == Role.GUEST:
        q = q.where(Order.created_by_user_id == user.id)
    return list(db.execute(q.order_by(Order.created_at.desc())).scalars().all())


def transition_order(db: Session, user: UserAccount, order_id: str, next_state: OrderState, reversal_reason: str | None) -> Order:
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise KeyError("Order not found.")
    if order.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")

    if next_state not in ALLOWED_ORDER_TRANSITIONS[order.state]:
        raise ValueError(f"Invalid order transition: {order.state.value} -> {next_state.value}")

    if next_state == OrderState.REFUNDED and not reversal_reason:
        raise ValueError("Refunds require a reversal reason.")

    order.transition_to(next_state)
    if next_state == OrderState.IN_PREP and order.service_start_at is None:
        order.service_start_at = _now()
    if user.role == Role.SERVICE_STAFF and order.service_staff_user_id is None:
        order.service_staff_user_id = user.id
    if next_state in {OrderState.DELIVERED, OrderState.CANCELED, OrderState.REFUNDED}:
        order.service_end_at = _now()

    if next_state == OrderState.REFUNDED:
        order.reversal_reason = reversal_reason
        db.add(
            FolioEntry(
                folio_id=order.folio_id,
                entry_type=FolioEntryType.ADJUSTMENT,
                amount=order.total_amount,
                payment_method=order.payment_method,
                note=f"Refund posted: {reversal_reason}",
            )
        )
    audit_event(db, user, "order_transition", "order", order.id, {"next_state": next_state.value})
    db.commit()
    log_event(logger, "finance", "order_transition", order_id=order.id, next_state=next_state.value)
    db.refresh(order)
    return order


def split_order_allocations(db: Session, user: UserAccount, order_id: str, allocations: list[dict[str, object]]) -> list[OrderAllocation]:
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise KeyError("Order not found.")
    if order.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    if not allocations:
        raise ValueError("At least one allocation is required.")

    normalized: list[dict[str, object]] = []
    total_units = 0
    for row in allocations:
        supplier = str(row.get("supplier", "")).strip()
        warehouse = str(row.get("warehouse", "")).strip()
        sla_tier = str(row.get("sla_tier", "")).strip()
        quantity = int(str(row.get("quantity", 0)))
        if not supplier or not warehouse or not sla_tier or quantity <= 0:
            raise ValueError("Each split row requires supplier, warehouse, SLA tier, and positive quantity.")
        total_units += quantity
        normalized.append({"supplier": supplier, "warehouse": warehouse, "sla_tier": sla_tier, "quantity": quantity})

    existing = db.execute(select(OrderAllocation).where(OrderAllocation.order_id == order.id)).scalars().all()
    for row in existing:
        db.delete(row)

    created: list[OrderAllocation] = []
    for row in normalized:
        allocation = OrderAllocation(
            organization_id=user.organization_id,
            order_id=order.id,
            supplier=str(row["supplier"]),
            warehouse=str(row["warehouse"]),
            sla_tier=str(row["sla_tier"]),
            quantity=int(str(row["quantity"])),
        )
        db.add(allocation)
        created.append(allocation)
    audit_event(db, user, "order_split_dimensions", "order", order.id, {"rows": str(len(created)), "units": str(total_units)})
    db.commit()
    log_event(logger, "finance", "order_split_dimensions", order_id=order.id, rows=len(created))
    return created


def merge_order_allocations(
    db: Session,
    user: UserAccount,
    order_id: str,
    supplier: str,
    warehouse: str,
    sla_tier: str,
) -> list[OrderAllocation]:
    existing = list_order_allocations(db, user, order_id)
    total_units = sum((row.quantity for row in existing), 0)
    if total_units <= 0:
        total_units = 1
    merged = split_order_allocations(
        db,
        user,
        order_id,
        [{"supplier": supplier, "warehouse": warehouse, "sla_tier": sla_tier, "quantity": total_units}],
    )
    audit_event(
        db,
        user,
        "order_merge_dimensions",
        "order",
        order_id,
        {"supplier": supplier, "warehouse": warehouse, "units": str(total_units)},
    )
    db.commit()
    return merged


def list_order_allocations(db: Session, user: UserAccount, order_id: str) -> list[OrderAllocation]:
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise KeyError("Order not found.")
    if order.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    return list(db.execute(select(OrderAllocation).where(OrderAllocation.order_id == order.id)).scalars().all())
