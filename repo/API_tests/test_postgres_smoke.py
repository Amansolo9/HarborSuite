from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.core.config import settings


@pytest.mark.skipif(
    "postgresql" not in (os.getenv("DATABASE_URL", "") or settings.database_url),
    reason="PostgreSQL smoke only runs with PostgreSQL DATABASE_URL",
)
def test_postgres_smoke_login_and_overview() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "gm@seabreeze.local", "password": "Harbor#2026!"},
            headers={"x-harborsuite-auth-mode": "bearer"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        overview = client.get("/api/v1/operations/overview", headers={"Authorization": f"Bearer {token}"})
        assert overview.status_code == 200
