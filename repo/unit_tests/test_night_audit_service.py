from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base, Folio, FolioEntry, FolioEntryType
from backend.services.night_audit import NightAuditService


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_night_audit_passes_balanced_folio() -> None:
    db = _session()
    folio = Folio(organization_id="org-1", guest_name="Guest", room_number="100")
    db.add(folio)
    db.flush()
    db.add_all(
        [
            FolioEntry(folio_id=folio.id, entry_type=FolioEntryType.CHARGE, amount=Decimal("200.00"), note="Charge"),
            FolioEntry(folio_id=folio.id, entry_type=FolioEntryType.PAYMENT, amount=Decimal("200.00"), note="Payment"),
        ]
    )
    db.commit()

    result = NightAuditService(db).run()
    assert result["passed"] is True


def test_night_audit_fails_imbalanced_folio() -> None:
    db = _session()
    folio = Folio(organization_id="org-1", guest_name="Guest", room_number="101")
    db.add(folio)
    db.flush()
    db.add(FolioEntry(folio_id=folio.id, entry_type=FolioEntryType.CHARGE, amount=Decimal("240.00"), note="Charge"))
    db.add(FolioEntry(folio_id=folio.id, entry_type=FolioEntryType.PAYMENT, amount=Decimal("200.00"), note="Payment"))
    db.commit()

    result = NightAuditService(db).run()
    assert result["passed"] is False
    assert result["failed_count"] == 1
