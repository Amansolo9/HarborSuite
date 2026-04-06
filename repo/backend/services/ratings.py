from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.models import Order, OrderState, Rating, Role, UserAccount
from backend.services.audit import audit_event


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def submit_rating(
    db: Session,
    user: UserAccount,
    to_username: str,
    score: int,
    comment: str | None,
    order_id: str,
) -> Rating:
    target = db.execute(select(UserAccount).where(UserAccount.username == to_username)).scalar_one_or_none()
    if target is None:
        raise KeyError("Target user not found.")
    if target.organization_id != user.organization_id:
        raise PermissionError("Cross-organization rating is not allowed.")
    if target.id == user.id:
        raise ValueError("Self-rating is not allowed.")
    if score < 1 or score > 5:
        raise ValueError("Score must be between 1 and 5.")

    user_is_guest = user.role == Role.GUEST
    target_is_guest = target.role == Role.GUEST
    if user_is_guest == target_is_guest:
        raise ValueError("Mutual ratings must be between guest and staff roles.")

    if not order_id:
        raise ValueError("Ratings require order_id for interaction verification.")

    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None or order.organization_id != user.organization_id:
        raise KeyError("Order not found.")
    if order.state not in {OrderState.DELIVERED, OrderState.REFUNDED, OrderState.CANCELED}:
        raise ValueError("Ratings are allowed only after service completion.")

    completion_time = order.service_end_at or order.updated_at or order.created_at
    if _now() - _as_utc(completion_time) > timedelta(days=7):
        raise ValueError("Ratings must be submitted within 7 days of service completion.")

    guest_id = order.created_by_user_id
    eligible_staff_roles = {Role.SERVICE_STAFF}
    if user_is_guest and user.id != guest_id:
        raise PermissionError("Guest rater must be the guest from the completed order.")
    if target_is_guest and target.id != guest_id:
        raise PermissionError("Guest target must be the guest from the completed order.")
    if user_is_guest and target.role not in eligible_staff_roles:
        raise PermissionError("Guest can rate only staff who participated in service delivery roles.")
    if target_is_guest and user.role not in eligible_staff_roles:
        raise PermissionError("Only service staff can rate guests for completed orders.")
    if user_is_guest and target.role == Role.SERVICE_STAFF and order.service_staff_user_id != target.id:
        raise PermissionError("Guest can rate only service staff assigned to the completed order.")
    if target_is_guest and user.role == Role.SERVICE_STAFF and order.service_staff_user_id != user.id:
        raise PermissionError("Service staff can rate only guests from orders they handled.")

    existing = db.execute(
        select(Rating).where(and_(Rating.from_user_id == user.id, Rating.to_user_id == target.id, Rating.order_id == order_id))
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("A rating for this relationship and order already exists.")

    rating = Rating(
        organization_id=user.organization_id,
        order_id=order_id,
        from_user_id=user.id,
        to_user_id=target.id,
        score=score,
        comment=comment,
    )
    db.add(rating)
    db.flush()
    audit_event(db, user, "rating_submitted", "rating", rating.id, {"score": str(score), "to": target.username})
    db.commit()
    db.refresh(rating)
    return rating


def list_my_ratings(db: Session, user: UserAccount) -> list[Rating]:
    return list(
        db.execute(
            select(Rating)
            .where(Rating.organization_id == user.organization_id)
            .where((Rating.from_user_id == user.id) | (Rating.to_user_id == user.id))
            .order_by(Rating.created_at.desc())
        )
        .scalars()
        .all()
    )
