from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, require_roles
from backend.core.database import get_db
from backend.models import ContentStatus, Rating, Role, UserAccount
from backend.schemas.pms import (
    ComplaintPacketResponse,
    ComplaintRequest,
    ComplaintResponse,
    ContentReleaseRequest,
    ContentReleaseResponse,
    RatingRequest,
    RatingResponse,
)
from backend.services.complaints import complaint_packet, create_complaint
from backend.services.content import approve_release, create_release, list_releases, rollback_release
from backend.services.ratings import list_my_ratings, submit_rating

router = APIRouter(tags=["pms"])


def _page(items: list, limit: int, offset: int) -> list:
    return items[offset : offset + limit]


def _serialize_release(release) -> ContentReleaseResponse:
    return ContentReleaseResponse(
        id=release.id,
        title=release.title,
        content_type=release.content_type,
        version=release.version,
        status=release.status,
        target_roles=[Role(role) for role in release.target_roles.split(",") if role],
        target_tags=[tag for tag in release.target_tags.split(",") if tag],
        target_organizations=[org for org in (release.target_organizations or "all").split(",") if org],
        readership_count=release.readership_count,
        rollback_of_id=release.rollback_of_id,
    )


def _serialize_rating(row: Rating) -> RatingResponse:
    return RatingResponse(
        id=row.id,
        from_user_id=row.from_user_id,
        to_user_id=row.to_user_id,
        score=row.score,
        comment=row.comment,
        order_id=row.order_id,
        created_at=row.created_at,
    )


@router.post("/content/releases", response_model=ContentReleaseResponse)
def create_release_route(
    payload: ContentReleaseRequest,
    user: UserAccount = Depends(require_roles(Role.CONTENT_EDITOR)),
    db: Session = Depends(get_db),
) -> ContentReleaseResponse:
    return _serialize_release(
        create_release(
            db,
            user,
            payload.title,
            payload.body,
            payload.content_type,
            payload.target_roles,
            payload.target_tags,
            payload.target_organizations,
        )
    )


@router.get("/content/releases", response_model=list[ContentReleaseResponse])
def list_releases_route(
    status_filter: ContentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ContentReleaseResponse]:
    rows = list_releases(db, user)
    if status_filter is not None:
        rows = [row for row in rows if row.status == status_filter]
    return [_serialize_release(release) for release in _page(rows, limit, offset)]


@router.post("/content/releases/{release_id}/approve", response_model=ContentReleaseResponse)
def approve_release_route(
    release_id: str,
    user: UserAccount = Depends(require_roles(Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> ContentReleaseResponse:
    try:
        release = approve_release(db, user, release_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _serialize_release(release)


@router.post("/content/releases/{release_id}/rollback", response_model=ContentReleaseResponse)
def rollback_release_route(
    release_id: str,
    user: UserAccount = Depends(require_roles(Role.CONTENT_EDITOR, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> ContentReleaseResponse:
    try:
        release = rollback_release(db, user, release_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _serialize_release(release)


@router.post("/complaints", response_model=ComplaintResponse)
def create_complaint_route(
    payload: ComplaintRequest,
    user: UserAccount = Depends(require_roles(Role.GUEST, Role.SERVICE_STAFF)),
    db: Session = Depends(get_db),
) -> ComplaintResponse:
    try:
        complaint = create_complaint(db, user, payload.folio_id, payload.subject, payload.detail, payload.service_rating, payload.violation_flag)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ComplaintResponse(
        id=complaint.id,
        subject=complaint.subject,
        service_rating=complaint.service_rating,
        violation_flag=complaint.violation_flag,
        folio_id=complaint.folio_id,
    )


@router.get("/complaints/{complaint_id}/packet", response_model=ComplaintPacketResponse)
def complaint_packet_route(
    complaint_id: str,
    user: UserAccount = Depends(require_roles(Role.GUEST, Role.SERVICE_STAFF, Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> ComplaintPacketResponse:
    try:
        return ComplaintPacketResponse(**complaint_packet(db, user, complaint_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/complaints/{complaint_id}/packet/download")
def complaint_packet_download_route(
    complaint_id: str,
    user: UserAccount = Depends(require_roles(Role.GUEST, Role.SERVICE_STAFF, Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        packet = complaint_packet(db, user, complaint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return FileResponse(
        path=packet["packet_path"],
        media_type=packet["packet_media_type"],
        filename=packet["packet_filename"],
    )


@router.post("/ratings", response_model=RatingResponse)
def submit_rating_route(
    payload: RatingRequest,
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RatingResponse:
    try:
        rating = submit_rating(
            db,
            user,
            to_username=payload.to_username,
            score=payload.score,
            comment=payload.comment,
            order_id=payload.order_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_rating(rating)


@router.get("/ratings/me", response_model=list[RatingResponse])
def list_my_ratings_route(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RatingResponse]:
    return [_serialize_rating(row) for row in _page(list_my_ratings(db, user), limit, offset)]
