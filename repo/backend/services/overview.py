from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import AuditEvent, ComplaintCase, ContentRelease, ContentStatus, ExportBundle, Folio, FolioStatus, Order, OrderState, Organization, Role, UserAccount


def overview(db: Session, user: UserAccount) -> dict[str, object]:
    property_name = db.execute(select(Organization.name).where(Organization.id == user.organization_id)).scalar_one()
    open_folios = db.execute(
        select(func.count()).select_from(Folio).where(Folio.organization_id == user.organization_id, Folio.status != FolioStatus.CLOSED)
    ).scalar_one()
    active_orders_q = select(func.count()).select_from(Order).where(
        Order.organization_id == user.organization_id,
        Order.state.not_in([OrderState.CANCELED, OrderState.REFUNDED]),
    )
    if user.role == Role.GUEST:
        active_orders_q = active_orders_q.where(Order.created_by_user_id == user.id)
    active_orders = db.execute(active_orders_q).scalar_one()

    pending_content = db.execute(
        select(func.count()).select_from(ContentRelease).where(
            ContentRelease.organization_id == user.organization_id,
            ContentRelease.status == ContentStatus.PENDING_APPROVAL,
        )
    ).scalar_one()
    open_complaints = db.execute(select(func.count()).select_from(ComplaintCase).where(ComplaintCase.organization_id == user.organization_id)).scalar_one()
    pending_exports = db.execute(select(func.count()).select_from(ExportBundle).where(ExportBundle.organization_id == user.organization_id)).scalar_one()

    return {
        "property_name": property_name,
        "role": user.role,
        "open_folios": open_folios,
        "active_orders": active_orders,
        "pending_content": pending_content,
        "open_complaints": open_complaints,
        "unread_releases": 0,
        "pending_exports": pending_exports,
    }


def list_audit_events(db: Session, user: UserAccount) -> list[AuditEvent]:
    q = select(AuditEvent).where(AuditEvent.organization_id == user.organization_id).order_by(AuditEvent.created_at.desc())
    return list(db.execute(q).scalars().all())
