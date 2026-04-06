from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.core.config import settings
from backend.core.logging import get_logger, log_event
from backend.models import DayCloseRun, DayCloseStatus, Folio, FolioEntry, FolioEntryType, FolioStatus, Organization, UserAccount
from backend.services.audit import audit_event
from backend.services.night_audit import NightAuditService

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _now().date().isoformat()


def run_day_close(
    db: Session,
    actor: UserAccount | None = None,
    business_date: str | None = None,
    organization_ids: list[str] | None = None,
) -> dict[str, object]:
    business_day = business_date or _today()
    organizations_query = select(Organization)
    if organization_ids:
        organizations_query = organizations_query.where(Organization.id.in_(organization_ids))
    organizations = db.execute(organizations_query).scalars().all()
    all_runs: list[dict[str, object]] = []

    room_rate = Decimal(settings.day_close_room_rate)
    tax_rate = Decimal(settings.day_close_tax_rate)
    tax_amount = (room_rate * tax_rate).quantize(Decimal("0.01"))

    for org in organizations:
        existing = db.execute(
            select(DayCloseRun).where(DayCloseRun.organization_id == org.id, DayCloseRun.business_date == business_day)
        ).scalar_one_or_none()
        if existing is not None:
            all_runs.append(
                {
                    "organization_id": org.id,
                    "business_date": existing.business_date,
                    "status": existing.status.value,
                    "failed_count": existing.failed_count,
                    "auto_posted_entries": existing.auto_posted_entries,
                    "already_ran": True,
                }
            )
            continue

        folios = list(
            db.execute(
                select(Folio)
                .options(selectinload(Folio.entries))
                .where(Folio.organization_id == org.id, Folio.status != FolioStatus.CLOSED)
            )
            .scalars()
            .all()
        )

        auto_posted_entries = 0
        for folio in folios:
            folio.status = FolioStatus.IN_AUDIT
            db.add(
                FolioEntry(
                    folio_id=folio.id,
                    entry_type=FolioEntryType.CHARGE,
                    amount=room_rate,
                    note=f"Auto-post room charge for business date {business_day}",
                )
            )
            db.add(
                FolioEntry(
                    folio_id=folio.id,
                    entry_type=FolioEntryType.CHARGE,
                    amount=tax_amount,
                    note=f"Auto-post occupancy tax for business date {business_day}",
                )
            )
            auto_posted_entries += 2

        db.flush()
        audit_result = NightAuditService(db).run(organization_id=org.id)
        failed_count = int(audit_result["failed_count"])
        passed = failed_count == 0

        if passed:
            for folio in folios:
                folio.status = FolioStatus.CLOSED
                folio.closed_at = _now()
            status = DayCloseStatus.COMPLETED
        else:
            db.rollback()
            for folio in folios:
                db.refresh(folio)
            status = DayCloseStatus.FAILED
            auto_posted_entries = 0

        run = DayCloseRun(
            organization_id=org.id,
            business_date=business_day,
            cutoff_time=settings.day_close_cutoff_time,
            status=status,
            failed_count=failed_count,
            auto_posted_entries=auto_posted_entries,
            details_json=json.dumps(audit_result),
        )
        db.add(run)
        db.flush()

        if actor is not None:
            audit_event(
                db,
                actor,
                "day_close_run",
                "day_close",
                run.id,
                {"organization_id": org.id, "business_date": business_day, "status": status.value},
            )
        log_event(
            logger,
            "finance",
            "day_close_run",
            organization_id=org.id,
            business_date=business_day,
            status=status.value,
            failed_count=failed_count,
        )
        all_runs.append(
            {
                "organization_id": org.id,
                "business_date": business_day,
                "status": status.value,
                "failed_count": failed_count,
                "auto_posted_entries": auto_posted_entries,
                "already_ran": False,
            }
        )

    db.commit()
    return {
        "business_date": business_day,
        "cutoff_time": settings.day_close_cutoff_time,
        "runs": all_runs,
        "passed": all(run["failed_count"] == 0 for run in all_runs),
    }
