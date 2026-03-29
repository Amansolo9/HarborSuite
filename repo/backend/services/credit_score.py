from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CreditEvent, CreditProfile, UserAccount
from backend.services.audit import audit_event
from backend.services.masking import mask_sensitive_note


class CreditScoreService:
    BASE_SCORE = Decimal("700")
    RATING_WEIGHT = Decimal("30")

    @classmethod
    def calculate(cls, rating: int, penalties: list[Decimal] | None = None) -> int:
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5.")

        total_penalty = sum(penalties or [], Decimal("0"))
        score = cls.BASE_SCORE + (Decimal(rating) - Decimal("3")) * cls.RATING_WEIGHT - total_penalty
        clamped = max(Decimal("300"), min(Decimal("850"), score))
        return int(clamped)


def record_credit_event(
    db: Session,
    actor: UserAccount,
    username: str,
    rating: int,
    penalties: list[Decimal],
    violation: bool,
    note: str | None,
) -> CreditProfile:
    target = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
    if target is None:
        raise KeyError("Target user not found.")
    if target.organization_id != actor.organization_id:
        raise PermissionError("Cross-organization credit scoring is not allowed.")

    penalty_sum = sum(penalties, Decimal("0.00"))
    profile = db.execute(select(CreditProfile).where(CreditProfile.user_id == target.id)).scalar_one_or_none()
    if profile is None:
        profile = CreditProfile(organization_id=target.organization_id, user_id=target.id, score=700, violation_count=0, last_rating=3)
        db.add(profile)
        db.flush()

    event = CreditEvent(
        organization_id=target.organization_id,
        user_id=target.id,
        rating=rating,
        penalty=penalty_sum,
        violation=violation,
        note=note,
        created_by_user_id=actor.id,
    )
    db.add(event)
    if violation:
        profile.violation_count += 1
    profile.last_rating = rating
    profile.score = CreditScoreService.calculate(rating=rating, penalties=[penalty_sum + Decimal(profile.violation_count * 50)])
    db.flush()
    audit_event(db, actor, "credit_profile_updated", "credit_profile", profile.id, {"target": username, "score": str(profile.score)})
    db.commit()
    db.refresh(profile)
    return profile


def get_credit_profile(db: Session, actor: UserAccount, username: str) -> dict[str, object]:
    target = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
    if target is None:
        raise KeyError("Target user not found.")
    if target.organization_id != actor.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    profile = db.execute(select(CreditProfile).where(CreditProfile.user_id == target.id)).scalar_one_or_none()
    if profile is None:
        profile = CreditProfile(organization_id=target.organization_id, user_id=target.id, score=700, violation_count=0, last_rating=3)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    events = list(
        db.execute(select(CreditEvent).where(CreditEvent.user_id == target.id).order_by(CreditEvent.created_at.desc()).limit(20)).scalars().all()
    )
    return {
        "username": target.username,
        "score": int(profile.score),
        "violation_count": int(profile.violation_count),
        "last_rating": int(profile.last_rating),
        "events": [
            {
                "rating": str(event.rating),
                "penalty": str(event.penalty),
                "violation": str(event.violation).lower(),
                "note": mask_sensitive_note(event.note or "", actor.role),
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }
