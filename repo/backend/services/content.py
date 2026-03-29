from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.models import ContentReadEvent, ContentRelease, ContentStatus, ContentType, Organization, Role, UserAccount
from backend.services.audit import audit_event


def create_release(
    db: Session,
    user: UserAccount,
    title: str,
    body: str,
    content_type: ContentType,
    target_roles: list[Role],
    target_tags: list[str],
    target_organizations: list[str],
) -> ContentRelease:
    release = ContentRelease(
        organization_id=user.organization_id,
        title=title,
        body=body,
        content_type=content_type,
        version=1,
        status=ContentStatus.PENDING_APPROVAL,
        target_roles=",".join(sorted({role.value for role in target_roles})),
        target_tags=",".join(sorted(set(target_tags))),
        target_organizations=",".join(sorted(set(target_organizations))) or "all",
    )
    db.add(release)
    db.flush()
    audit_event(db, user, "content_created", "content_release", release.id, {"title": title})
    db.commit()
    db.refresh(release)
    return release


def list_releases(db: Session, user: UserAccount) -> list[ContentRelease]:
    org_code = db.execute(select(Organization.code).where(Organization.id == user.organization_id)).scalar_one_or_none() or ""
    user_org_targets = {user.organization_id, org_code, "all"}
    releases = list(
        db.execute(
            select(ContentRelease)
            .where(
                or_(
                    ContentRelease.organization_id == user.organization_id,
                    ContentRelease.status == ContentStatus.APPROVED,
                )
            )
            .order_by(ContentRelease.created_at.desc())
        )
        .scalars()
        .all()
    )
    visible: list[ContentRelease] = []
    user_tags = {tag.strip() for tag in user.audience_tags.split(",") if tag.strip()}
    if not user_tags:
        user_tags = {"all"}

    for release in releases:
        privileged_own = release.organization_id == user.organization_id and user.role in {Role.CONTENT_EDITOR, Role.GENERAL_MANAGER}
        if not privileged_own and release.status != ContentStatus.APPROVED:
            continue
        if privileged_own:
            visible.append(release)
            continue
        roles = {item for item in release.target_roles.split(",") if item}
        tags = {item for item in release.target_tags.split(",") if item}
        orgs = {item for item in (release.target_organizations or "all").split(",") if item}
        tag_match = "all" in tags or bool(tags.intersection(user_tags))
        org_match = bool(orgs.intersection(user_org_targets))
        if user.role.value in roles and tag_match and org_match:
            read = db.execute(
                select(ContentReadEvent).where(
                    and_(
                        ContentReadEvent.organization_id == user.organization_id,
                        ContentReadEvent.release_id == release.id,
                        ContentReadEvent.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if read is None:
                db.add(ContentReadEvent(organization_id=user.organization_id, release_id=release.id, user_id=user.id))
                release.readership_count += 1
                audit_event(db, user, "content_read", "content_release", release.id, {"tag_match": "true"})
            visible.append(release)
    db.commit()
    return visible


def approve_release(db: Session, user: UserAccount, release_id: str) -> ContentRelease:
    release = db.execute(select(ContentRelease).where(ContentRelease.id == release_id)).scalar_one_or_none()
    if release is None:
        raise KeyError("Release not found.")
    if release.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")
    release.status = ContentStatus.APPROVED
    audit_event(db, user, "content_approved", "content_release", release.id, {"version": str(release.version)})
    db.commit()
    db.refresh(release)
    return release


def rollback_release(db: Session, user: UserAccount, release_id: str) -> ContentRelease:
    previous = db.execute(select(ContentRelease).where(ContentRelease.id == release_id)).scalar_one_or_none()
    if previous is None:
        raise KeyError("Release not found.")
    if previous.organization_id != user.organization_id:
        raise PermissionError("Cross-organization access is not allowed.")

    release = ContentRelease(
        organization_id=previous.organization_id,
        title=f"Rollback of {previous.title}",
        body=previous.body,
        content_type=previous.content_type,
        version=previous.version + 1,
        status=ContentStatus.ROLLED_BACK,
        target_roles=previous.target_roles,
        target_tags=previous.target_tags,
        target_organizations=previous.target_organizations,
        readership_count=previous.readership_count,
        rollback_of_id=previous.id,
    )
    db.add(release)
    db.flush()
    audit_event(db, user, "content_rollback", "content_release", release.id, {"rollback_of_id": previous.id})
    db.commit()
    db.refresh(release)
    return release
