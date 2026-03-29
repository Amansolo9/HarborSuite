from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logging import get_logger, log_event
from backend.models import Role, UserAccount
from backend.services.auth import resolve_user

bearer_scheme = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserAccount:
    token = credentials.credentials if credentials is not None else request.cookies.get(settings.session_cookie_name)
    if not token:
        log_event(logger, "authz", "missing_credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        return resolve_user(db, token)
    except (PermissionError, ValueError) as exc:
        log_event(logger, "authz", "invalid_token", reason=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_roles(*allowed_roles: Role) -> Callable[[UserAccount], UserAccount]:
    def dependency(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in allowed_roles:
            log_event(logger, "authz", "role_denied", username=user.username, role=user.role.value)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions.")
        return user

    return dependency


def session_idle_minutes() -> int:
    return settings.session_idle_minutes
