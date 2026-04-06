from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.core.config import settings
from backend.models import Folio, FolioEntryType


@dataclass
class NightAuditResult:
    folio_id: str
    charges: Decimal
    payments: Decimal
    adjustments: Decimal
    delta: Decimal
    passed: bool
    reason: str


class NightAuditService:
    TOLERANCE = Decimal("0.01")

    def __init__(self, db: Session):
        self.db = db

    def run(self, organization_id: str | None = None) -> dict[str, object]:
        query = select(Folio).options(selectinload(Folio.entries))
        if organization_id:
            query = query.where(Folio.organization_id == organization_id)
        folios = list(self.db.execute(query).scalars().all())
        results: list[dict[str, object]] = []

        for folio in folios:
            charges = Decimal("0.00")
            payments = Decimal("0.00")
            adjustments = Decimal("0.00")
            reversals = Decimal("0.00")
            for entry in folio.entries:
                if entry.entry_type == FolioEntryType.CHARGE:
                    charges += entry.amount
                elif entry.entry_type == FolioEntryType.PAYMENT:
                    payments += entry.amount
                elif entry.entry_type == FolioEntryType.ADJUSTMENT:
                    adjustments += entry.amount
                elif entry.entry_type == FolioEntryType.REVERSAL:
                    reversals += entry.amount
            delta = (charges - payments - adjustments - reversals).quantize(Decimal("0.01"))
            passed = abs(delta) <= self.TOLERANCE
            result = NightAuditResult(
                folio_id=folio.id,
                charges=charges,
                payments=payments,
                adjustments=adjustments,
                delta=delta,
                passed=passed,
                reason="Balanced within threshold" if passed else "Out of balance by more than $0.01",
            )
            results.append(
                {
                    "folio_id": result.folio_id,
                    "charges": str(result.charges),
                    "payments": str(result.payments),
                    "adjustments": str(result.adjustments),
                    "delta": str(result.delta),
                    "passed": result.passed,
                    "reason": result.reason,
                }
            )

        failed_count = len([line for line in results if not line["passed"]])
        return {
            "total_folios": len(results),
            "failed_count": failed_count,
            "passed": failed_count == 0,
            "cutoff_time": settings.day_close_cutoff_time,
            "results": results,
        }
