from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.security import hash_password
from backend.models import Base, Organization, Role, UserAccount
from backend.services.auth import authenticate_user


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_auth_logs_do_not_emit_password_or_token(caplog) -> None:
    db = _db()
    org = Organization(name="Org", code="org")
    db.add(org)
    db.flush()
    user = UserAccount(
        organization_id=org.id,
        username="user@test.local",
        full_name="User",
        role=Role.FINANCE,
        audience_tags="all",
        password_hash=hash_password("Strong#Pass123"),
    )
    db.add(user)
    db.commit()

    secret_password = "TopSecret#123"
    with caplog.at_level(logging.INFO):
        try:
            authenticate_user(db, "user@test.local", secret_password)
        except PermissionError:
            pass

    combined = "\n".join(message for message in caplog.messages)
    assert secret_password not in combined
    assert "Bearer" not in combined
