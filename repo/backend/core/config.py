from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    app_env: str
    database_url: str
    db_connect_retries: int
    db_connect_delay_seconds: float
    jwt_secret: str
    jwt_expire_minutes: int
    session_idle_minutes: int
    max_login_attempts: int
    lockout_minutes: int
    export_checksum_secret: str
    print_command_template: str
    frontend_dist_path: str
    day_close_cutoff_time: str
    day_close_room_rate: str
    day_close_tax_rate: str
    order_tax_rule_version: str
    order_catalog_path: str
    super_admin_usernames: tuple[str, ...]
    seed_demo_data: bool
    session_cookie_name: str
    session_cookie_secure: bool


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(parts)


settings = Settings(
    app_env=os.getenv("APP_ENV", "dev"),
    database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://harborsuite:harborsuite@localhost:5432/harborsuite"),
    db_connect_retries=int(os.getenv("DB_CONNECT_RETRIES", "30")),
    db_connect_delay_seconds=float(os.getenv("DB_CONNECT_DELAY_SECONDS", "1")),
    jwt_secret=os.getenv("JWT_SECRET", "harbor-suite-offline-secret"),
    jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "15")),
    session_idle_minutes=int(os.getenv("SESSION_IDLE_MINUTES", "15")),
    max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
    lockout_minutes=int(os.getenv("LOCKOUT_MINUTES", "15")),
    export_checksum_secret=os.getenv("EXPORT_CHECKSUM_SECRET", "offline-export-secret"),
    print_command_template=os.getenv("PRINT_COMMAND_TEMPLATE", ""),
    frontend_dist_path=os.getenv("FRONTEND_DIST_PATH", "frontend/dist"),
    day_close_cutoff_time=os.getenv("DAY_CLOSE_CUTOFF_TIME", "03:00"),
    day_close_room_rate=os.getenv("DAY_CLOSE_ROOM_RATE", "149.00"),
    day_close_tax_rate=os.getenv("DAY_CLOSE_TAX_RATE", "0.10"),
    order_tax_rule_version=os.getenv("ORDER_TAX_RULE_VERSION", "standard-2026"),
    order_catalog_path=os.getenv("ORDER_CATALOG_PATH", "data/order_catalog.json"),
    super_admin_usernames=_env_csv("SUPER_ADMIN_USERNAMES"),
    seed_demo_data=_env_bool("SEED_DEMO_DATA", True),
    session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "harborsuite_session"),
    session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", os.getenv("APP_ENV", "dev") != "dev"),
)
