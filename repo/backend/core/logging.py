from __future__ import annotations

import logging
from typing import Any


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, category: str, event: str, **fields: Any) -> None:
    context = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("category=%s event=%s %s", category, event, context)
