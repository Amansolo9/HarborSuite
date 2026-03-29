from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.core.logging import get_logger
from backend.models import AnalyticsSnapshot, ContentRelease, ContentStatus, DataLineage, DatasetVersion, MetricDefinition, Order, OrderState, UserAccount

logger = get_logger(__name__)


class AnalyticsService:
    SNAPSHOT_METRICS = {
        "gm_dashboard": [
            "scale_index",
            "churn_rate",
            "participation_rate",
            "order_volume",
            "fund_income_expense",
            "budget_execution",
            "approval_efficiency",
        ],
        "service_durations": ["service_duration_metrics"],
    }

    def __init__(self, db: Session):
        self.db = db

    def snapshot_provenance(self, user: UserAccount, snapshot_type: str) -> dict[str, object]:
        metric_names = self.SNAPSHOT_METRICS.get(snapshot_type)
        if not metric_names:
            raise ValueError("Unsupported snapshot_type.")

        bindings: list[dict[str, object]] = []
        for metric_name in metric_names:
            metric = self.db.execute(
                select(MetricDefinition)
                .where(MetricDefinition.organization_id == user.organization_id, MetricDefinition.metric_name == metric_name)
                .order_by(desc(MetricDefinition.version), desc(MetricDefinition.created_at))
            ).scalars().first()
            if metric is None:
                raise ValueError(f"Missing governance metric definition for '{metric_name}'.")

            lineage = self.db.execute(
                select(DataLineage)
                .where(DataLineage.organization_id == user.organization_id, DataLineage.metric_name == metric_name)
                .order_by(desc(DataLineage.created_at))
            ).scalars().first()
            if lineage is None:
                raise ValueError(f"Missing governance lineage binding for '{metric_name}'.")

            dataset = self.db.execute(
                select(DatasetVersion).where(
                    DatasetVersion.organization_id == user.organization_id,
                    DatasetVersion.id == lineage.dataset_version_id,
                )
            ).scalar_one_or_none()
            if dataset is None:
                raise ValueError(f"Dataset version not found for lineage metric '{metric_name}'.")

            bindings.append(
                {
                    "metric_name": metric.metric_name,
                    "metric_definition_id": metric.id,
                    "metric_version": metric.version,
                    "metric_source_query_ref": metric.source_query_ref,
                    "lineage_source_query_ref": lineage.source_query_ref,
                    "dataset_version_id": dataset.id,
                    "dataset_name": dataset.dataset_name,
                    "dataset_version": dataset.version,
                    "dataset_checksum": dataset.checksum,
                }
            )

        return {"snapshot_type": snapshot_type, "bindings": bindings}

    def gm_dashboard(self, user: UserAccount) -> dict[str, Decimal | int]:
        org = user.organization_id
        total_orders = int(self.db.execute(select(func.count()).select_from(Order).where(Order.organization_id == org)).scalar_one())
        delivered_orders = int(
            self.db.execute(
                select(func.count())
                .select_from(Order)
                .where(Order.organization_id == org, Order.state == OrderState.DELIVERED)
            ).scalar_one()
        )
        canceled_orders = int(
            self.db.execute(
                select(func.count())
                .select_from(Order)
                .where(Order.organization_id == org, Order.state == OrderState.CANCELED)
            ).scalar_one()
        )
        refunded_orders = int(
            self.db.execute(
                select(func.count())
                .select_from(Order)
                .where(Order.organization_id == org, Order.state == OrderState.REFUNDED)
            ).scalar_one()
        )
        gross_revenue = Decimal(
            str(
                self.db.execute(
                    select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.organization_id == org)
                ).scalar_one()
            )
        )
        refund_value = Decimal(
            str(
                self.db.execute(
                    select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                        Order.organization_id == org,
                        Order.state == OrderState.REFUNDED,
                    )
                ).scalar_one()
            )
        )
        pending_content = int(
            self.db.execute(
                select(func.count())
                .select_from(ContentRelease)
                .where(ContentRelease.organization_id == org, ContentRelease.status == ContentStatus.PENDING_APPROVAL)
            ).scalar_one()
        )
        approved_content = int(
            self.db.execute(
                select(func.count())
                .select_from(ContentRelease)
                .where(ContentRelease.organization_id == org, ContentRelease.status == ContentStatus.APPROVED)
            ).scalar_one()
        )

        order_volume = total_orders
        churn_rate = Decimal("0.00") if total_orders == 0 else (Decimal(canceled_orders) / Decimal(total_orders) * Decimal("100")).quantize(Decimal("0.01"))
        participation_rate = (
            Decimal("0.00")
            if total_orders == 0
            else (Decimal(delivered_orders + refunded_orders) / Decimal(total_orders) * Decimal("100")).quantize(Decimal("0.01"))
        )
        fund_income_expense = (gross_revenue - refund_value).quantize(Decimal("0.01"))
        budget_execution = Decimal("0.00") if gross_revenue == 0 else (fund_income_expense / gross_revenue * Decimal("100")).quantize(Decimal("0.01"))
        approval_total = approved_content + pending_content
        approval_efficiency = Decimal("100.00") if approval_total == 0 else (
            Decimal(approved_content) / Decimal(approval_total) * Decimal("100")
        ).quantize(Decimal("0.01"))
        scale_index = Decimal(order_volume).quantize(Decimal("0.01"))

        return {
            "scale_index": scale_index,
            "churn_rate": churn_rate,
            "participation_rate": participation_rate,
            "order_volume": order_volume,
            "fund_income_expense": fund_income_expense,
            "budget_execution": budget_execution,
            "approval_efficiency": approval_efficiency,
        }

    def service_duration_metrics(self, user: UserAccount) -> dict[str, object]:
        orders = list(
            self.db.query(Order)
            .filter(Order.organization_id == user.organization_id)
            .filter(Order.service_start_at.is_not(None))
            .filter(Order.service_end_at.is_not(None))
            .all()
        )
        grouped: dict[tuple[str, str], list[Decimal]] = {}
        users = {
            row.id: row
            for row in self.db.query(UserAccount).filter(UserAccount.organization_id == user.organization_id).all()
        }
        for order in orders:
            duration_minutes = Decimal(str((order.service_end_at - order.service_start_at).total_seconds() / 60)).quantize(
                Decimal("0.01")
            )
            items = json.loads(order.order_items_json)
            first_item = str(items[0].get("name", "generic")) if items else "generic"
            actor = users.get(order.created_by_user_id)
            actor_role = actor.role.value if actor is not None else "unknown"
            key = (actor_role, first_item)
            grouped.setdefault(key, []).append(duration_minutes)

        metrics: list[dict[str, object]] = []
        for (actor_role, order_type), values in grouped.items():
            average = (sum(values, Decimal("0.00")) / Decimal(len(values))).quantize(Decimal("0.01"))
            metrics.append(
                {
                    "actor_role": actor_role,
                    "order_type": order_type,
                    "completed_orders": len(values),
                    "avg_duration_minutes": average,
                }
            )
        return {"metrics": sorted(metrics, key=lambda row: (str(row["actor_role"]), str(row["order_type"])))}

    def record_snapshot(self, organization_id: str, snapshot_type: str, payload: dict[str, object], provenance: dict[str, object]) -> None:
        self.db.add(
            AnalyticsSnapshot(
                organization_id=organization_id,
                snapshot_type=snapshot_type,
                payload_json=json.dumps({"snapshot": payload, "provenance": provenance}, default=str, sort_keys=True),
            )
        )
        self.db.commit()
