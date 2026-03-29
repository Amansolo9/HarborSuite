from __future__ import annotations

from backend.models import Role


def mask_sensitive_note(note: str, role: Role) -> str:
    if role in {Role.FINANCE, Role.GENERAL_MANAGER}:
        return note
    if len(note) <= 6:
        return "***"
    return f"{note[:2]}{'*' * (len(note) - 4)}{note[-2:]}"
