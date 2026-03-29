from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.security import hash_password, validate_password_policy
from backend.models import Base, Organization, Role, UserAccount
from backend.services.auth import authenticate_user


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_password_policy_rejects_weak_password() -> None:
    try:
        validate_password_policy("weakpass")
        assert False, "weak password should fail policy"
    except ValueError:
        pass


def test_lockout_applies_after_threshold_failures() -> None:
    db = _db()
    org = Organization(name="Org", code="org")
    db.add(org)
    db.flush()
    user = UserAccount(
        organization_id=org.id,
        username="lock@test.local",
        full_name="Lock User",
        role=Role.FINANCE,
        audience_tags="all",
        password_hash=hash_password("Strong#Pass123"),
    )
    db.add(user)
    db.commit()

    for _ in range(5):
        try:
            authenticate_user(db, "lock@test.local", "wrong")
        except PermissionError:
            pass

    refreshed = db.query(UserAccount).filter(UserAccount.username == "lock@test.local").one()
    assert refreshed.locked_until is not None
