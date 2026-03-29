from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, require_roles
from backend.core.database import get_db
from backend.models import FolioStatus, Role, UserAccount
from backend.schemas.pms import (
    FolioAdjustmentRequest,
    FolioChargeRequest,
    FolioInvoiceResponse,
    FolioMergeRequest,
    FolioPaymentRequest,
    FolioReceiptResponse,
    FolioReversalRequest,
    FolioSplitAllocationResponse,
    FolioSplitRequest,
    FolioSummaryResponse,
    PrintJobResponse,
)
from backend.services.folio import (
    build_invoice,
    build_receipt,
    folio_balance,
    get_folio_for_user,
    list_folios,
    list_split_allocations,
    merge_folios,
    post_adjustment,
    post_charge,
    post_payment,
    post_reversal,
    split_folio,
)
from backend.services.printer import queue_receipt_print
from backend.services.printer import queue_invoice_print

router = APIRouter(tags=["pms"])


def _page(items: list, limit: int, offset: int) -> list:
    return items[offset : offset + limit]


@router.get("/folios", response_model=list[FolioSummaryResponse])
def list_folios_route(
    status_filter: FolioStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FolioSummaryResponse]:
    folios = list_folios(db, user)
    if status_filter is not None:
        folios = [folio for folio in folios if folio.status == status_filter]
    folios = _page(folios, limit, offset)
    return [
        FolioSummaryResponse(
            id=folio.id,
            guest_name=folio.guest_name,
            room_number=folio.room_number,
            status=folio.status.value,
            balance_due=folio_balance(folio),
        )
        for folio in folios
    ]


@router.post("/folios/{folio_id}/payments", response_model=FolioReceiptResponse)
def post_payment_route(
    folio_id: str,
    payload: FolioPaymentRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = post_payment(db, user, folio_id, payload.amount, payload.payment_method, payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.post("/folios/{folio_id}/charges", response_model=FolioReceiptResponse)
def post_charge_route(
    folio_id: str,
    payload: FolioChargeRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = post_charge(db, user, folio_id, payload.amount, payload.reason, payload.payment_method)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.post("/folios/{folio_id}/adjustments", response_model=FolioReceiptResponse)
def post_adjustment_route(
    folio_id: str,
    payload: FolioAdjustmentRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE)),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = post_adjustment(db, user, folio_id, payload.amount, payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.post("/folios/{folio_id}/reversals", response_model=FolioReceiptResponse)
def post_reversal_route(
    folio_id: str,
    payload: FolioReversalRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = post_reversal(db, user, folio_id, payload.amount, payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.post("/folios/{folio_id}/split")
def split_folio_route(
    folio_id: str,
    payload: FolioSplitRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return split_folio(db, user, folio_id, payload.allocations)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/folios/{folio_id}/splits", response_model=list[FolioSplitAllocationResponse])
def list_folio_splits_route(
    folio_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FolioSplitAllocationResponse]:
    try:
        rows = list_split_allocations(db, user, folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [
        FolioSplitAllocationResponse(source_folio_id=row.source_folio_id, child_folio_id=row.child_folio_id, amount=row.amount)
        for row in _page(rows, limit, offset)
    ]


@router.post("/folios/merge", response_model=FolioReceiptResponse)
def merge_folios_route(
    payload: FolioMergeRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE)),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = merge_folios(db, user, payload.primary_folio_id, payload.secondary_folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.get("/folios/{folio_id}/receipt", response_model=FolioReceiptResponse)
def folio_receipt(
    folio_id: str,
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FolioReceiptResponse:
    try:
        folio = get_folio_for_user(db, user, folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioReceiptResponse(**build_receipt(user, folio))


@router.get("/folios/{folio_id}/invoice", response_model=FolioInvoiceResponse)
def folio_invoice(
    folio_id: str,
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FolioInvoiceResponse:
    try:
        folio = get_folio_for_user(db, user, folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FolioInvoiceResponse(**build_invoice(user, folio))


@router.post("/folios/{folio_id}/print", response_model=PrintJobResponse)
def print_folio_receipt(
    folio_id: str,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> PrintJobResponse:
    try:
        folio = get_folio_for_user(db, user, folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    receipt = build_receipt(user, folio)
    job = queue_receipt_print(db, user, folio_id, receipt)
    return PrintJobResponse(
        print_job_id=job.id,
        status=job.status,
        queue_path=f"data/print_queue/{user.organization_id}/print-job-{job.id}.json",
    )


@router.post("/folios/{folio_id}/print-invoice", response_model=PrintJobResponse)
def print_folio_invoice(
    folio_id: str,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE)),
    db: Session = Depends(get_db),
) -> PrintJobResponse:
    try:
        folio = get_folio_for_user(db, user, folio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    invoice = build_invoice(user, folio)
    job = queue_invoice_print(db, user, folio_id, invoice)
    return PrintJobResponse(
        print_job_id=job.id,
        status=job.status,
        queue_path=f"data/print_queue/{user.organization_id}/print-job-{job.id}.json",
    )
