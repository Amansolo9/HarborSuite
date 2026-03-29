from __future__ import annotations

from contextlib import asynccontextmanager
import threading
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    while not stop_event.is_set():
        try:
            now = datetime.now()
            cutoff_hour, cutoff_minute = [int(part) for part in settings.day_close_cutoff_time.split(":", 1)]
            if now.hour == cutoff_hour and now.minute == cutoff_minute:
                with SessionLocal() as db:
                    run_day_close(db, actor=None)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "offline-ready"}
