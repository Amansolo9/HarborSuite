from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, require_roles
from backend.core.database import get_db
from backend.models import OrderAllocation, OrderState, Role, UserAccount
from backend.schemas.pms import (
    ConfirmQuoteRequest,
    ConfirmQuoteResponse,
    CreateOrderRequest,
    OrderAllocationResponse,
    OrderCatalogItemResponse,
    OrderMergeRequest,
    OrderResponse,
    OrderSplitRequest,
    OrderTransitionRequest,
)
from backend.services.orders import (
    confirm_quote,
    create_order,
    list_catalog_items,
    list_order_allocations,
    list_orders,
    merge_order_allocations,
    parse_order_items,
    split_order_allocations,
    transition_order,
)

router = APIRouter(tags=["pms"])


def _page(items: list, limit: int, offset: int) -> list:
    return items[offset : offset + limit]


def _serialize_order(order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        folio_id=order.folio_id,
        organization_id=order.organization_id,
        state=order.state,
        subtotal_amount=order.subtotal_amount,
        packaging_fee=order.packaging_fee,
        service_fee=order.service_fee,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        order_items=parse_order_items(order),
        delivery_window_start=order.delivery_window_start,
        delivery_window_end=order.delivery_window_end,
        tax_reconfirm_by=order.tax_reconfirm_by,
        order_note=order.order_note,
        reversal_reason=order.reversal_reason,
        created_by_user_id=order.created_by_user_id,
        service_end_at=order.service_end_at,
    )


def _serialize_allocation(row: OrderAllocation) -> OrderAllocationResponse:
    return OrderAllocationResponse(
        supplier=row.supplier,
        warehouse=row.warehouse,
        sla_tier=row.sla_tier,
        quantity=row.quantity,
    )


@router.post("/orders/confirm-quote", response_model=ConfirmQuoteResponse)
def confirm_quote_route(
    payload: ConfirmQuoteRequest,
    user: UserAccount = Depends(require_roles(Role.GUEST, Role.FRONT_DESK)),
    db: Session = Depends(get_db),
) -> ConfirmQuoteResponse:
    try:
        quote = confirm_quote(
            db,
            user,
            folio_id=payload.folio_id,
            items=[item.model_dump(mode="json") for item in payload.items],
            payment_method=payload.payment_method,
            packaging_fee=payload.packaging_fee,
            service_fee=payload.service_fee,
            tax_rate=payload.tax_rate,
            delivery_window_start=payload.delivery_window_start,
            delivery_window_end=payload.delivery_window_end,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConfirmQuoteResponse(reconfirm_token=quote.reconfirm_token, expires_at=quote.expires_at, quote_hash=quote.quote_hash)


@router.get("/orders/catalog", response_model=list[OrderCatalogItemResponse])
def order_catalog_route(user: UserAccount = Depends(get_current_user)) -> list[OrderCatalogItemResponse]:
    if user.role not in {Role.GUEST, Role.FRONT_DESK, Role.SERVICE_STAFF, Role.FINANCE, Role.GENERAL_MANAGER}:
        raise HTTPException(status_code=403, detail="Role is not permitted to view order catalog.")
    return [OrderCatalogItemResponse(**item) for item in list_catalog_items()]


@router.post("/orders", response_model=OrderResponse)
def create_order_route(
    payload: CreateOrderRequest,
    user: UserAccount = Depends(require_roles(Role.GUEST, Role.FRONT_DESK)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = create_order(
            db=db,
            user=user,
            folio_id=payload.folio_id,
            items=[item.model_dump(mode="json") for item in payload.items],
            payment_method=payload.payment_method,
            packaging_fee=payload.packaging_fee,
            service_fee=payload.service_fee,
            tax_rate=payload.tax_rate,
            order_note=payload.order_note,
            delivery_window_start=payload.delivery_window_start,
            delivery_window_end=payload.delivery_window_end,
            price_confirmed_at=payload.price_confirmed_at,
            reconfirm_token=payload.reconfirm_token,
        )
    except (KeyError, ValueError, PermissionError) as exc:
        code = 404 if isinstance(exc, KeyError) else 409
        if isinstance(exc, PermissionError):
            code = 403
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _serialize_order(order)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders_route(
    state: OrderState | None = Query(default=None),
    sort: str = Query(default="created_desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderResponse]:
    rows = list_orders(db, user)
    if state is not None:
        rows = [row for row in rows if row.state == state]
    if sort == "created_asc":
        rows = sorted(rows, key=lambda row: row.created_at)
    elif sort == "created_desc":
        rows = sorted(rows, key=lambda row: row.created_at, reverse=True)
    else:
        raise HTTPException(status_code=400, detail="Unsupported sort option.")
    return [_serialize_order(order) for order in _page(rows, limit, offset)]


@router.post("/orders/{order_id}/transition", response_model=OrderResponse)
def transition_order_route(
    order_id: str,
    payload: OrderTransitionRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.SERVICE_STAFF, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = transition_order(db, user, order_id, payload.next_state, payload.reversal_reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_order(order)


@router.post("/orders/{order_id}/split", response_model=list[OrderAllocationResponse])
def split_order_route(
    order_id: str,
    payload: OrderSplitRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.SERVICE_STAFF, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> list[OrderAllocationResponse]:
    try:
        rows = split_order_allocations(db, user, order_id, [row.model_dump() for row in payload.allocations])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [_serialize_allocation(row) for row in rows]


@router.post("/orders/{order_id}/merge", response_model=list[OrderAllocationResponse])
def merge_order_route(
    order_id: str,
    payload: OrderMergeRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.SERVICE_STAFF, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> list[OrderAllocationResponse]:
    try:
        rows = merge_order_allocations(db, user, order_id, payload.supplier, payload.warehouse, payload.sla_tier)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [_serialize_allocation(row) for row in rows]


@router.get("/orders/{order_id}/allocations", response_model=list[OrderAllocationResponse])
def list_order_allocations_route(
    order_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderAllocationResponse]:
    try:
        rows = list_order_allocations(db, user, order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [_serialize_allocation(row) for row in _page(rows, limit, offset)]
