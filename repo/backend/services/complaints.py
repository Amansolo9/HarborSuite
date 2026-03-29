from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import ComplaintCase, Order, Role, UserAccount
from backend.services.audit import audit_event
from backend.services.folio import get_folio_for_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_complaint(
    db: Session,
    user: UserAccount,
    folio_id: str,
    subject: str,
    detail: str,
    service_rating: int,
    violation_flag: bool,
) -> ComplaintCase:
    folio = get_folio_for_user(db, user, folio_id)
    last_order_at = db.execute(select(func.max(Order.created_at)).where(Order.folio_id == folio.id)).scalar_one_or_none()
    if last_order_at is None:
        raise ValueError("Complaint requires a related order on the folio.")
    if _now() - _as_utc(last_order_at) > timedelta(days=7):
        raise ValueError("Complaints must be filed within 7 days of the related service order.")

    complaint = ComplaintCase(
        organization_id=folio.organization_id,
        folio_id=folio.id,
        reported_by_user_id=user.id,
        subject=subject,
        detail=detail,
        service_rating=service_rating,
        violation_flag=violation_flag,
    )
    db.add(complaint)
    db.flush()
    audit_event(db, user, "complaint_created", "complaint", complaint.id, {"violation_flag": str(violation_flag).lower()})
    db.commit()
    db.refresh(complaint)
    return complaint


def _write_pdf_packet(path: Path, complaint: ComplaintCase) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, text="HarborSuite Arbitration Packet", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Complaint ID: {complaint.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Subject: {complaint.subject}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Service rating: {complaint.service_rating}", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 8, text=f"Detail: {complaint.detail}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def complaint_packet(db: Session, user: UserAccount, complaint_id: str) -> dict[str, object]:
    complaint = db.execute(select(ComplaintCase).where(ComplaintCase.id == complaint_id)).scalar_one_or_none()
    if complaint is None:
        raise KeyError("Complaint not found.")
    if complaint.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    if user.role in {Role.GUEST, Role.SERVICE_STAFF} and complaint.reported_by_user_id != user.id:
        raise PermissionError("Guests and service staff can only access complaint packets they reported.")
    if user.role not in {Role.GUEST, Role.SERVICE_STAFF, Role.FINANCE, Role.GENERAL_MANAGER}:
        raise PermissionError("Role is not permitted to access complaint packets.")

    output_path = Path("data/evidence") / f"complaint-{complaint.id}.pdf"
    _write_pdf_packet(output_path, complaint)
    bytes_data = output_path.read_bytes()
    checksum = hashlib.sha256(bytes_data).hexdigest()
    manifest = {
        "complaint_id": complaint.id,
        "checksum": checksum,
        "pdf_path": str(output_path),
    }
    manifest_path = output_path.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    audit_event(db, user, "complaint_packet_exported", "complaint", complaint.id, {"checksum": checksum[:12]})
    db.commit()
    return {
        "complaint_id": complaint.id,
        "checksum": checksum,
        "sections": ["Guest statement", "Folio timeline", "Service rating trend", "Policy and violation notes"],
        "packet_filename": output_path.name,
        "packet_path": str(output_path),
        "packet_media_type": "application/pdf",
        "manifest_path": str(manifest_path),
        "download_url": f"/api/v1/complaints/{complaint.id}/packet/download",
    }
