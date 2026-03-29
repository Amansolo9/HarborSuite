from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.core.config import settings
from backend.core.logging import get_logger, log_event
from backend.core.security import create_access_token, decode_access_token, verify_password
from backend.models import SessionToken, UserAccount
from backend.services.audit import audit_event

logger = get_logger(__name__)


class AuthError(PermissionError):
    def __init__(self, message: str, *, lockout_seconds: int | None = None) -> None:
        super().__init__(message)
        self.lockout_seconds = lockout_seconds


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _lockout_seconds_remaining(locked_until: datetime, now: datetime) -> int:
    return max(1, int((_as_utc(locked_until) - now).total_seconds()))


def authenticate_user(db: Session, username: str, password: str) -> UserAccount:
    user = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
    if user is None:
        log_event(logger, "auth", "login_failed", username=username, reason="unknown_user")
        raise AuthError("Invalid username or password.")

    now = _now()
    if user.locked_until and now < _as_utc(user.locked_until):
        lockout_seconds = _lockout_seconds_remaining(user.locked_until, now)
        log_event(logger, "auth", "login_denied", username=username, reason="account_locked")
        raise AuthError("Account temporarily locked due to repeated failed sign-in attempts.", lockout_seconds=lockout_seconds)

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        log_event(logger, "auth", "login_failed", username=username, reason="invalid_password")
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.failed_login_attempts = 0
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            log_event(logger, "auth", "account_locked", username=username, minutes=settings.lockout_minutes)
            db.commit()
            raise AuthError(
                "Account temporarily locked due to repeated failed sign-in attempts.",
                lockout_seconds=settings.lockout_minutes * 60,
            )
        db.commit()
        raise AuthError("Invalid username or password.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_activity_at = now
    return user


def create_session(db: Session, user: UserAccount) -> str:
    token = create_access_token(user.id, {"org": user.organization_id, "role": user.role.value, "sid": str(uuid.uuid4())})
    session = SessionToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        created_at=_now(),
        last_seen_at=_now(),
        expires_at=_now() + timedelta(minutes=settings.jwt_expire_minutes),
    )
    db.add(session)
    db.flush()
    audit_event(db, user, "login", "session", session.id, {"role": user.role.value})
    db.commit()
    log_event(logger, "auth", "login_success", username=user.username, role=user.role.value)
    return token


def resolve_user(db: Session, token: str) -> UserAccount:
    decode_access_token(token)
    token_hash = _hash_token(token)
    session = db.execute(select(SessionToken).where(SessionToken.token_hash == token_hash)).scalar_one_or_none()
    if session is None:
        log_event(logger, "auth", "session_denied", reason="missing_session")
        raise PermissionError("Session not found.")

    now = _now()
    expires_at = _as_utc(session.expires_at)
    last_seen_at = _as_utc(session.last_seen_at)
    if now > expires_at or now - last_seen_at > timedelta(minutes=settings.session_idle_minutes):
        db.delete(session)
        db.commit()
        log_event(logger, "auth", "session_expired", user_id=session.user_id)
        raise PermissionError("Session timed out due to inactivity.")

    user = db.execute(select(UserAccount).where(UserAccount.id == session.user_id)).scalar_one()
    user.last_activity_at = now
    session.last_seen_at = now
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        log_event(logger, "auth", "session_denied", reason="stale_session")
        raise PermissionError("Session not found.") from exc
    return user


def revoke_session(db: Session, token: str) -> None:
    token_hash = _hash_token(token)
    session = db.execute(select(SessionToken).where(SessionToken.token_hash == token_hash)).scalar_one_or_none()
    if session is None:
        return
    db.delete(session)
    db.commit()
