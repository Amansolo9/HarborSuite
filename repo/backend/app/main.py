from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
import threading
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.routes import router as api_router
from backend.core.config import settings
from backend.core.database import SessionLocal, initialize_database
from backend.core.logging import configure_logging, get_logger, log_event
from backend.core.runtime_guard import enforce_secure_runtime
from backend.services.day_close import run_day_close
from backend.services.seed import seed_if_empty

logger = get_logger(__name__)


def _scheduler_stop_event() -> threading.Event:
    return threading.Event()


def _day_close_loop(stop_event: threading.Event) -> None:
    last_run_date: str | None = None
    while not stop_event.is_set():
        try:
            now = datetime.now()
            cutoff_hour, cutoff_minute = [int(part) for part in settings.day_close_cutoff_time.split(":", 1)]
            today = now.strftime("%Y-%m-%d")
            cutoff_reached = now.hour > cutoff_hour or (now.hour == cutoff_hour and now.minute >= cutoff_minute)
            if cutoff_reached and last_run_date != today:
                with SessionLocal() as db:
                    run_day_close(db, actor=None)
                last_run_date = today
        except Exception as exc:
            log_event(logger, "scheduler", "day_close_loop_error", error=str(exc))
            logger.exception("Day-close scheduler loop failed")
        stop_event.wait(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    enforce_secure_runtime()
    initialize_database()
    with SessionLocal() as db:
        seed_if_empty(db)
    stop_event = _scheduler_stop_event()
    scheduler = threading.Thread(target=_day_close_loop, args=(stop_event,), daemon=True)
    scheduler.start()
    try:
        yield
    finally:
        stop_event.set()
        scheduler.join(timeout=1)


app = FastAPI(
    title="HarborSuite Offline PMS",
    description="Offline-first hotel commerce and PMS API with RBAC, audit logging, exports, and guest-service workflows.",
    version="0.2.0",
    lifespan=lifespan,
)
CSRF_COOKIE_NAME = "harborsuite_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PATHS = {"/api/v1/auth/login"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        if request.method not in CSRF_SAFE_METHODS and request.url.path not in CSRF_EXEMPT_PATHS:
            auth_header = request.headers.get("authorization") or ""
            uses_bearer = auth_header.lower().startswith("bearer ")
            session_cookie = request.cookies.get(settings.session_cookie_name)
            if session_cookie and not uses_bearer:
                header_token = request.headers.get(CSRF_HEADER_NAME)
                if not csrf_cookie or not header_token or header_token != csrf_cookie:
                    return Response("CSRF token missing or invalid", status_code=403)
        response = await call_next(request)
        if not csrf_cookie:
            token = secrets.token_urlsafe(32)
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                httponly=False,
                secure=settings.session_cookie_secure,
                samesite="lax",
                path="/",
            )
        return response


app.add_middleware(CSRFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "offline-ready"}
