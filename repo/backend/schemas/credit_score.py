from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CreditScoreRequest(BaseModel):
    username: str
    rating: int = Field(ge=1, le=5)
    penalties: list[Decimal] = Field(default_factory=list)
    violation: bool = False
    note: str | None = Field(default=None, max_length=255)


class CreditScoreResponse(BaseModel):
    username: str
    score: int
    violation_count: int
    last_rating: int


class CreditProfileResponse(BaseModel):
    username: str
    score: int
    violation_count: int
    last_rating: int
    events: list[dict[str, str]]
