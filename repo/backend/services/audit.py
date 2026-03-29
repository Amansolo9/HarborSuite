from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import AuditEvent, UserAccount


def audit_event(
    db: Session,
    actor: UserAccount,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, str],
) -> None:
    event = AuditEvent(
        id=str(uuid.uuid4()),
        actor=actor.username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organization_id=actor.organization_id,
        metadata_json=json.dumps(metadata),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
