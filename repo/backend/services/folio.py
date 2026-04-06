from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.logging import get_logger, log_event
from backend.models import Folio, FolioEntry, FolioEntryType, FolioSplitAllocation, FolioStatus, PaymentMethod, Role, UserAccount
from backend.services.audit import audit_event
from backend.services.masking import mask_sensitive_note

logger = get_logger(__name__)


def get_folio_for_user(db: Session, user: UserAccount, folio_id: str) -> Folio:
    folio = db.execute(select(Folio).where(Folio.id == folio_id)).scalar_one_or_none()
    if folio is None:
        raise KeyError("Folio not found.")
    if folio.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    if user.role == Role.GUEST and folio.guest_user_id != user.id:
        raise PermissionError("Guests can only access their own folios.")
    return folio


def list_folios(db: Session, user: UserAccount) -> list[Folio]:
    q = select(Folio).where(Folio.organization_id == user.organization_id)
    if user.role == Role.GUEST:
        q = q.where(Folio.guest_user_id == user.id)
    return list(db.execute(q).scalars().all())


def post_payment(db: Session, user: UserAccount, folio_id: str, amount: Decimal, method: PaymentMethod, note: str | None) -> Folio:
    folio = get_folio_for_user(db, user, folio_id)
    db.add(
        FolioEntry(
            folio_id=folio.id,
            entry_type=FolioEntryType.PAYMENT,
            amount=amount,
            payment_method=method,
            note=note or "Payment received",
        )
    )
    audit_event(db, user, "folio_payment", "folio", folio.id, {"amount": str(amount), "payment_method": method.value})
    db.commit()
    log_event(logger, "finance", "folio_payment_posted", folio_id=folio.id, amount=str(amount), method=method.value)
    db.refresh(folio)
    return folio


def post_charge(db: Session, user: UserAccount, folio_id: str, amount: Decimal, reason: str, method: PaymentMethod | None) -> Folio:
    folio = get_folio_for_user(db, user, folio_id)
    db.add(
        FolioEntry(
            folio_id=folio.id,
            entry_type=FolioEntryType.CHARGE,
            amount=amount,
            payment_method=method,
            note=f"Manual charge: {reason}",
        )
    )
    audit_event(db, user, "folio_manual_charge", "folio", folio.id, {"amount": str(amount), "reason": reason})
    db.commit()
    log_event(logger, "finance", "folio_manual_charge_posted", folio_id=folio.id, amount=str(amount))
    db.refresh(folio)
    return folio


def post_adjustment(db: Session, user: UserAccount, folio_id: str, amount: Decimal, reason: str) -> Folio:
    folio = get_folio_for_user(db, user, folio_id)
    db.add(
        FolioEntry(
            folio_id=folio.id,
            entry_type=FolioEntryType.ADJUSTMENT,
            amount=amount,
            note=reason,
        )
    )
    audit_event(db, user, "folio_adjustment", "folio", folio.id, {"amount": str(amount)})
    db.commit()
    log_event(logger, "finance", "folio_adjustment_posted", folio_id=folio.id, amount=str(amount))
    db.refresh(folio)
    return folio


def post_reversal(db: Session, user: UserAccount, folio_id: str, amount: Decimal, reason: str) -> Folio:
    folio = get_folio_for_user(db, user, folio_id)
    db.add(
        FolioEntry(
            folio_id=folio.id,
            entry_type=FolioEntryType.REVERSAL,
            amount=amount,
            note=f"Reversal: {reason}",
        )
    )
    audit_event(db, user, "folio_reversal", "folio", folio.id, {"amount": str(amount), "reason": reason})
    db.commit()
    log_event(logger, "finance", "folio_reversal_posted", folio_id=folio.id, amount=str(amount))
    db.refresh(folio)
    return folio


def folio_balance(folio: Folio) -> Decimal:
    balance = Decimal("0.00")
    for entry in folio.entries:
        if entry.entry_type == FolioEntryType.CHARGE:
            balance += entry.amount
        elif entry.entry_type in {FolioEntryType.PAYMENT, FolioEntryType.ADJUSTMENT, FolioEntryType.REVERSAL}:
            balance -= entry.amount
    return balance


def split_folio(db: Session, user: UserAccount, folio_id: str, allocations: list[Decimal]) -> dict[str, object]:
    folio = get_folio_for_user(db, user, folio_id)
    normalized = [amount.quantize(Decimal("0.01")) for amount in allocations]
    if sum(normalized, Decimal("0.00")).quantize(Decimal("0.01")) != folio_balance(folio).quantize(Decimal("0.01")):
        raise ValueError("Split allocations must equal current folio balance.")
    split_rows: list[dict[str, object]] = []
    for index, amount in enumerate(normalized, start=1):
        child = Folio(
            organization_id=folio.organization_id,
            guest_user_id=folio.guest_user_id,
            guest_name=folio.guest_name,
            room_number=f"{folio.room_number}-S{index}",
        )
        db.add(child)
        db.flush()
        db.add(
            FolioEntry(
                folio_id=child.id,
                entry_type=FolioEntryType.CHARGE,
                amount=amount,
                note=f"Split from folio {folio.id[:8]}",
            )
        )
        db.add(
            FolioEntry(
                folio_id=folio.id,
                entry_type=FolioEntryType.ADJUSTMENT,
                amount=amount,
                note=f"Split allocation moved to {child.id[:8]}",
            )
        )
        db.add(
            FolioSplitAllocation(
                organization_id=folio.organization_id,
                source_folio_id=folio.id,
                child_folio_id=child.id,
                amount=amount,
                created_by_user_id=user.id,
            )
        )
        split_rows.append({"source_folio_id": folio.id, "child_folio_id": child.id, "amount": amount})
    audit_event(db, user, "folio_split", "folio", folio.id, {"parts": str(len(allocations))})
    db.commit()
    return {"folio_id": folio.id, "allocations": split_rows}


def list_split_allocations(db: Session, user: UserAccount, folio_id: str) -> list[FolioSplitAllocation]:
    folio = get_folio_for_user(db, user, folio_id)
    return list(
        db.execute(
            select(FolioSplitAllocation)
            .where(FolioSplitAllocation.organization_id == user.organization_id)
            .where(FolioSplitAllocation.source_folio_id == folio.id)
            .order_by(FolioSplitAllocation.created_at.desc())
        )
        .scalars()
        .all()
    )


def merge_folios(db: Session, user: UserAccount, primary_folio_id: str, secondary_folio_id: str) -> Folio:
    primary = get_folio_for_user(db, user, primary_folio_id)
    secondary = get_folio_for_user(db, user, secondary_folio_id)
    for entry in list(secondary.entries):
        entry.folio_id = primary.id
    secondary.status = FolioStatus.CLOSED
    audit_event(db, user, "folio_merge", "folio", primary.id, {"secondary": secondary.id})
    db.commit()
    db.refresh(primary)
    return primary


def build_receipt(user: UserAccount, folio: Folio) -> dict[str, object]:
    lines = [f"Guest: {folio.guest_name}", f"Room: {folio.room_number}", f"Balance due: {folio_balance(folio)}"]
    for entry in sorted(folio.entries, key=lambda x: x.created_at):
        safe_note = mask_sensitive_note(entry.note, user.role)
        lines.append(f"{entry.created_at.strftime('%Y-%m-%d %H:%M')} {entry.entry_type.value} {entry.amount} {safe_note}")
    return {
        "folio_id": folio.id,
        "guest_name": folio.guest_name,
        "room_number": folio.room_number,
        "balance_due": folio_balance(folio),
        "printable_lines": lines,
    }


def build_invoice(user: UserAccount, folio: Folio) -> dict[str, object]:
    invoice_id = f"INV-{folio.id[:8].upper()}"
    lines = [f"Invoice: {invoice_id}", f"Guest: {folio.guest_name}", f"Room: {folio.room_number}"]
    for entry in sorted(folio.entries, key=lambda x: x.created_at):
        safe_note = mask_sensitive_note(entry.note, user.role)
        lines.append(f"{entry.entry_type.value}: {entry.amount} ({safe_note})")
    lines.append(f"Total due: {folio_balance(folio)}")
    return {
        "folio_id": folio.id,
        "invoice_id": invoice_id,
        "guest_name": folio.guest_name,
        "room_number": folio.room_number,
        "balance_due": folio_balance(folio),
        "invoice_lines": lines,
    }
