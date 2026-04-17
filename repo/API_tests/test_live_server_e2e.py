"""End-to-end smoke tests that exercise the API over a real TCP socket.

Unlike the other API_tests modules which use FastAPI's in-process ASGI TestClient,
this module spawns a real uvicorn worker in a subprocess and talks to it via a
real HTTP client. This proves the full network stack, not just the ASGI pipeline.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    # Override the module-level autouse fixture from conftest.py: this suite
    # manages its own subprocess database, so we must not touch the shared
    # test engine (which may not even be reachable in this environment).
    yield


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except Exception as exc:
            last_exc = exc
        time.sleep(0.25)
    raise RuntimeError(f"Uvicorn did not become ready at {url}: {last_exc}")


@pytest.fixture(scope="module")
def live_server() -> Generator[str, None, None]:
    port = _pick_free_port()
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./live_e2e.db")
    env.setdefault("SEED_DEMO_DATA", "true")
    env.setdefault("APP_ENV", "dev")
    db_file = REPO_ROOT / "live_e2e.db"
    if db_file.exists():
        db_file.unlink()

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(f"{base_url}/health")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if db_file.exists():
            db_file.unlink()


def test_health_endpoint_over_real_network(live_server: str) -> None:
    response = httpx.get(f"{live_server}/health", timeout=5.0)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_login_and_authenticated_call_over_real_network(live_server: str) -> None:
    with httpx.Client(base_url=live_server, timeout=5.0) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "gm@seabreeze.local", "password": "Harbor#2026!"},
            headers={"x-harborsuite-auth-mode": "bearer"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert token

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "gm@seabreeze.local"


def test_unauthenticated_request_returns_401_over_real_network(live_server: str) -> None:
    response = httpx.get(f"{live_server}/api/v1/orders", timeout=5.0)
    assert response.status_code == 401
