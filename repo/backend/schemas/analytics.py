from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class GMDashboardResponse(BaseModel):
    scale_index: Decimal
    churn_rate: Decimal
    participation_rate: Decimal
    order_volume: int
    fund_income_expense: Decimal
    budget_execution: Decimal
    approval_efficiency: Decimal


class ServiceDurationMetric(BaseModel):
    actor_role: str
    order_type: str
    completed_orders: int
    avg_duration_minutes: Decimal


class ServiceDurationResponse(BaseModel):
    metrics: list[ServiceDurationMetric]


class AnalyticsSnapshotRequest(BaseModel):
    snapshot_type: str


class AnalyticsSnapshotResponse(BaseModel):
    snapshot_type: str
    status: str
    provenance_bindings: int
