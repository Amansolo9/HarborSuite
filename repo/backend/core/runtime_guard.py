from __future__ import annotations

from backend.core.config import settings


INSECURE_JWT_SECRETS = {
    "offline-demo-secret",
    "harbor-suite-offline-secret",
    "changeme",
}

INSECURE_EXPORT_SECRETS = {
    "offline-export-secret",
    "changeme",
}


def enforce_secure_runtime() -> None:
    if settings.app_env.lower() in {"dev", "development", "test"}:
        return

    if settings.jwt_secret in INSECURE_JWT_SECRETS:
        raise RuntimeError("Refusing startup: insecure JWT_SECRET configured for non-dev environment.")
    if settings.export_checksum_secret in INSECURE_EXPORT_SECRETS:
        raise RuntimeError("Refusing startup: insecure EXPORT_CHECKSUM_SECRET configured for non-dev environment.")
    if settings.seed_demo_data:
        raise RuntimeError("Refusing startup: SEED_DEMO_DATA must be disabled in non-dev environment.")
