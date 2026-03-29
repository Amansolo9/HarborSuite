from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.core.database import SessionLocal, engine
from backend.models import Base
from backend.services.seed import seed_if_empty


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient, username: str, password: str = "Harbor#2026!") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"x-harborsuite-auth-mode": "bearer"},
    )
    assert response.status_code == 200
    access_token = response.json().get("access_token")
    assert access_token
    return {"Authorization": f"Bearer {access_token}"}
