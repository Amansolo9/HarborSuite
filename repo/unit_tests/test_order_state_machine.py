import pytest
from datetime import datetime, timezone
from decimal import Decimal
import json

from backend.models import Order, OrderState, PaymentMethod


def _order(state: OrderState) -> Order:
    return Order(
        organization_id="org-1",
        folio_id="folio-1",
        created_by_user_id="user-1",
        state=state,
        subtotal_amount=Decimal("0.00"),
        packaging_fee=Decimal("0.00"),
        service_fee=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        payment_method=PaymentMethod.CASH,
        order_items_json=json.dumps([{"name": "tea", "quantity": 1, "unit_price": "5.00"}]),
        delivery_window_start=datetime.now(timezone.utc),
        delivery_window_end=datetime.now(timezone.utc),
        price_confirmed_at=datetime.now(timezone.utc),
        tax_reconfirm_by=datetime.now(timezone.utc),
    )


def test_valid_order_transition() -> None:
    order = _order(OrderState.CREATED)
    order.transition_to(OrderState.CONFIRMED)
    assert order.state == OrderState.CONFIRMED


def test_refund_transition_from_delivered_is_allowed() -> None:
    order = _order(OrderState.DELIVERED)
    order.transition_to(OrderState.REFUNDED)
    assert order.state == OrderState.REFUNDED


def test_invalid_order_transition_raises() -> None:
    order = _order(OrderState.DELIVERED)
    with pytest.raises(ValueError):
        order.transition_to(OrderState.IN_PREP)
