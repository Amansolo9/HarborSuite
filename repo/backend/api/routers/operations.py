from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, require_roles, session_idle_minutes
from backend.core.config import settings
from backend.core.database import get_db
from backend.models import Organization, Role, UserAccount
from backend.schemas.analytics import AnalyticsSnapshotRequest, AnalyticsSnapshotResponse, GMDashboardResponse, ServiceDurationResponse
from backend.schemas.credit_score import CreditProfileResponse, CreditScoreRequest, CreditScoreResponse
from backend.schemas.night_audit import DayCloseRequest, DayCloseResponse, NightAuditResponse, NightAuditRunRequest
from backend.schemas.pms import CurrentUserResponse, LoginRequest, LoginResponse, OverviewResponse
from backend.services.analytics import AnalyticsService
from backend.services.audit import audit_event
from backend.services.auth import AuthError, authenticate_user, create_session, revoke_session
from backend.services.credit_score import get_credit_profile, record_credit_event
from backend.services.day_close import run_day_close
from backend.services.night_audit import NightAuditService
from backend.services.overview import overview

router = APIRouter(tags=["pms"])


def _organization_name(db: Session, organization_id: str) -> str:
    org_name = db.execute(select(Organization.name).where(Organization.id == organization_id)).scalar_one_or_none()
    return org_name or ""


def _token_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.cookies.get(settings.session_cookie_name)


def _is_super_admin(user: UserAccount) -> bool:
    return user.username in settings.super_admin_usernames


def _resolve_org_scope(
    user: UserAccount,
    requested_org_id: str | None,
    all_organizations: bool,
) -> tuple[str | None, list[str] | None, bool]:
    if not requested_org_id and not all_organizations:
        return user.organization_id, [user.organization_id], False
    if not _is_super_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin override required for cross-organization scope.")
    if all_organizations:
        return None, None, True
    return requested_org_id, [requested_org_id] if requested_org_id else None, True


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    auth_mode = (request.headers.get("x-harborsuite-auth-mode") or "cookie").strip().lower()
    try:
        user = authenticate_user(db, payload.username, payload.password)
        token = create_session(db, user)
    except AuthError as exc:
        detail: str | dict[str, object] = str(exc)
        headers: dict[str, str] | None = None
        if exc.lockout_seconds is not None:
            detail = {"message": str(exc), "lockout_seconds": exc.lockout_seconds}
            headers = {"Retry-After": str(exc.lockout_seconds)}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers) from exc

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.jwt_expire_minutes * 60,
    )

    return LoginResponse(
        access_token=token if auth_mode == "bearer" else None,
        token_type="bearer" if auth_mode == "bearer" else None,
        expires_in_seconds=settings.jwt_expire_minutes * 60,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=_organization_name(db, user.organization_id),
    )


@router.get("/auth/me", response_model=CurrentUserResponse)
def me(user: UserAccount = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=_organization_name(db, user.organization_id),
        session_idle_minutes=session_idle_minutes(),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_route(
    request: Request,
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    token = _token_from_request(request)
    if token:
        revoke_session(db, token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@router.get("/operations/overview", response_model=OverviewResponse)
def operations_overview(user: UserAccount = Depends(get_current_user), db: Session = Depends(get_db)) -> OverviewResponse:
    return OverviewResponse(**overview(db, user))


@router.post("/credit-score/calculate", response_model=CreditScoreResponse)
def calculate_credit_score(
    payload: CreditScoreRequest,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> CreditScoreResponse:
    try:
        profile = record_credit_event(
            db,
            actor=user,
            username=payload.username,
            rating=payload.rating,
            penalties=payload.penalties,
            violation=payload.violation,
            note=payload.note,
        )
    except (ValueError, KeyError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreditScoreResponse(
        username=payload.username,
        score=profile.score,
        violation_count=profile.violation_count,
        last_rating=profile.last_rating,
    )


@router.get("/credit-score/{username}", response_model=CreditProfileResponse)
def get_credit_profile_route(
    username: str,
    user: UserAccount = Depends(require_roles(Role.FRONT_DESK, Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> CreditProfileResponse:
    try:
        data = get_credit_profile(db, user, username)
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CreditProfileResponse(**data)


@router.post("/night-audit/run", response_model=NightAuditResponse)
def run_night_audit(
    payload: NightAuditRunRequest | None = None,
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> NightAuditResponse:
    request_payload = payload if payload is not None else NightAuditRunRequest()
    organization_id, _, used_override = _resolve_org_scope(user, request_payload.organization_id, request_payload.all_organizations)
    if used_override:
        audit_event(
            db,
            user,
            "night_audit_scope_override",
            "night_audit",
            organization_id or "all",
            {"requested_org": organization_id or "all"},
        )
    return NightAuditResponse(**NightAuditService(db).run(organization_id=organization_id))


@router.post("/day-close/run", response_model=DayCloseResponse)
def run_day_close_route(
    payload: DayCloseRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> DayCloseResponse:
    organization_id, organization_ids, used_override = _resolve_org_scope(user, payload.organization_id, payload.all_organizations)
    if used_override:
        audit_event(
            db,
            user,
            "day_close_scope_override",
            "day_close",
            organization_id or "all",
            {"requested_org": organization_id or "all"},
        )
    return DayCloseResponse(**run_day_close(db, actor=user, business_date=payload.business_date, organization_ids=organization_ids))


@router.get("/analytics/gm-dashboard", response_model=GMDashboardResponse)
def gm_dashboard(
    db: Session = Depends(get_db),
    user: UserAccount = Depends(require_roles(Role.GENERAL_MANAGER)),
) -> GMDashboardResponse:
    return GMDashboardResponse(**AnalyticsService(db).gm_dashboard(user))


@router.get("/analytics/service-durations", response_model=ServiceDurationResponse)
def service_duration_dashboard(
    db: Session = Depends(get_db),
    user: UserAccount = Depends(require_roles(Role.SERVICE_STAFF, Role.FINANCE, Role.GENERAL_MANAGER)),
) -> ServiceDurationResponse:
    return ServiceDurationResponse(**AnalyticsService(db).service_duration_metrics(user))


@router.post("/analytics/snapshots", response_model=AnalyticsSnapshotResponse)
def create_analytics_snapshot(
    payload: AnalyticsSnapshotRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
) -> AnalyticsSnapshotResponse:
    service = AnalyticsService(db)
    try:
        provenance = service.snapshot_provenance(user, payload.snapshot_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if payload.snapshot_type == "gm_dashboard":
        snapshot_payload = service.gm_dashboard(user)
    elif payload.snapshot_type == "service_durations":
        snapshot_payload = service.service_duration_metrics(user)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported snapshot_type.")
    service.record_snapshot(user.organization_id, payload.snapshot_type, snapshot_payload, provenance)
    return AnalyticsSnapshotResponse(snapshot_type=payload.snapshot_type, status="recorded", provenance_bindings=len(provenance.get("bindings", [])))
