from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging import get_logger, log_event
from backend.models import ComplaintCase, ExportBundle, Folio, Order, UserAccount
from backend.services.audit import audit_event

logger = get_logger(__name__)
_EXPORT_TYPE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{2,48}$")


def _compute_checksum(payload_text: str) -> str:
    raw = f"{settings.export_checksum_secret}|{payload_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_payload(db: Session, user: UserAccount, export_type: str, scope: str, generated_at: datetime) -> dict[str, object]:
    return {
        "organization_id": user.organization_id,
        "export_type": export_type,
        "scope": scope,
        "generated_at": generated_at.isoformat(),
        "summary": {
            "folios": db.execute(select(func.count()).select_from(Folio).where(Folio.organization_id == user.organization_id)).scalar_one(),
            "orders": db.execute(select(func.count()).select_from(Order).where(Order.organization_id == user.organization_id)).scalar_one(),
            "complaints": db.execute(
                select(func.count()).select_from(ComplaintCase).where(ComplaintCase.organization_id == user.organization_id)
            ).scalar_one(),
        },
    }


def _sanitize_export_type(export_type: str) -> str:
    cleaned = export_type.strip()
    if not _EXPORT_TYPE_PATTERN.fullmatch(cleaned):
        raise ValueError("Invalid export type format.")
    return cleaned


def _write_payload(storage_path: str, payload_text: str, checksum: str) -> None:
    base_dir = Path("data") / "offline_exports"
    base_resolved = base_dir.resolve()
    full_path = (Path("data") / storage_path).resolve()
    if base_resolved not in full_path.parents:
        raise ValueError("Export path escapes offline export directory.")
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(payload_text, encoding="utf-8")
    verify_text = full_path.read_text(encoding="utf-8")
    if _compute_checksum(verify_text) != checksum:
        raise RuntimeError("Export integrity verification failed after write.")


def create_export(db: Session, user: UserAccount, export_type: str, scope: str) -> ExportBundle:
    export_type = _sanitize_export_type(export_type)
    now = datetime.now(timezone.utc)
    payload = _build_payload(db, user, export_type, scope, now)
    payload_text = json.dumps(payload, indent=2, sort_keys=True)
    checksum = _compute_checksum(payload_text)
    storage_path = f"offline_exports/{user.organization_id}/{export_type}-{checksum[:12]}.json"

    try:
        _write_payload(storage_path, payload_text, checksum)
    except Exception as exc:
        log_event(logger, "export", "write_failed", organization_id=user.organization_id, reason=str(exc))
        raise

    export = ExportBundle(
        organization_id=user.organization_id,
        export_type=export_type,
        scope=scope,
        checksum=checksum,
        storage_path=storage_path,
    )
    db.add(export)
    db.flush()
    audit_event(db, user, "export_created", "export", export.id, {"type": export_type, "scope": scope})
    db.commit()
    db.refresh(export)
    log_event(logger, "export", "write_success", export_id=export.id, path=storage_path)
    return export
