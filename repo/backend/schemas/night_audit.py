from __future__ import annotations

from pydantic import BaseModel


class NightAuditLine(BaseModel):
    folio_id: str
    charges: str
    payments: str
    adjustments: str
    delta: str
    passed: bool
    reason: str


class NightAuditResponse(BaseModel):
    total_folios: int
    failed_count: int
    passed: bool
    cutoff_time: str
    results: list[NightAuditLine]


class NightAuditRunRequest(BaseModel):
    organization_id: str | None = None
    all_organizations: bool = False


class DayCloseRequest(BaseModel):
    business_date: str | None = None
    organization_id: str | None = None
    all_organizations: bool = False


class DayCloseOrgRun(BaseModel):
    organization_id: str
    business_date: str
    status: str
    failed_count: int
    auto_posted_entries: int
    already_ran: bool


class DayCloseResponse(BaseModel):
    business_date: str
    cutoff_time: str
    passed: bool
    runs: list[DayCloseOrgRun]
