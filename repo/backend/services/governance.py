from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DataDictionaryField, DataLineage, DatasetVersion, MetricDefinition, UserAccount
from backend.services.audit import audit_event


def create_metric_definition(
    db: Session,
    user: UserAccount,
    metric_name: str,
    description: str,
    source_query_ref: str,
    version: int,
) -> MetricDefinition:
    metric = MetricDefinition(
        organization_id=user.organization_id,
        metric_name=metric_name,
        description=description,
        source_query_ref=source_query_ref,
        version=version,
    )
    db.add(metric)
    db.flush()
    audit_event(db, user, "governance_metric_created", "metric_definition", metric.id, {"metric": metric_name})
    db.commit()
    db.refresh(metric)
    return metric


def register_dataset_version(
    db: Session,
    user: UserAccount,
    dataset_name: str,
    version: str,
    schema: dict[str, object],
) -> DatasetVersion:
    schema_json = json.dumps(schema, sort_keys=True)
    dataset = DatasetVersion(
        organization_id=user.organization_id,
        dataset_name=dataset_name,
        version=version,
        schema_json=schema_json,
        checksum=hashlib.sha256(schema_json.encode("utf-8")).hexdigest(),
    )
    db.add(dataset)
    db.flush()

    for field_name, data_type in schema.items():
        db.add(
            DataDictionaryField(
                organization_id=user.organization_id,
                dataset_name=dataset_name,
                field_name=str(field_name),
                data_type=str(data_type),
                sensitivity="internal",
                description=f"{dataset_name}.{field_name}",
            )
        )

    audit_event(db, user, "governance_dataset_registered", "dataset_version", dataset.id, {"dataset": dataset_name})
    db.commit()
    db.refresh(dataset)
    return dataset


def register_lineage(
    db: Session,
    user: UserAccount,
    metric_name: str,
    dataset_version_id: str,
    source_tables: list[str],
    source_query_ref: str,
) -> DataLineage:
    dataset = db.execute(select(DatasetVersion).where(DatasetVersion.id == dataset_version_id)).scalar_one_or_none()
    if dataset is None or dataset.organization_id != user.organization_id:
        raise KeyError("Dataset version not found.")

    lineage = DataLineage(
        organization_id=user.organization_id,
        metric_name=metric_name,
        dataset_version_id=dataset_version_id,
        source_tables=",".join(source_tables),
        source_query_ref=source_query_ref,
    )
    db.add(lineage)
    db.flush()
    audit_event(db, user, "governance_lineage_registered", "data_lineage", lineage.id, {"metric": metric_name})
    db.commit()
    db.refresh(lineage)
    return lineage


def list_lineage(db: Session, user: UserAccount) -> list[DataLineage]:
    return list(
        db.execute(select(DataLineage).where(DataLineage.organization_id == user.organization_id).order_by(DataLineage.created_at.desc()))
        .scalars()
        .all()
    )


def export_dictionary(db: Session, user: UserAccount) -> dict[str, object]:
    rows = list(
        db.execute(
            select(DataDictionaryField)
            .where(DataDictionaryField.organization_id == user.organization_id)
            .order_by(DataDictionaryField.dataset_name, DataDictionaryField.field_name)
        )
        .scalars()
        .all()
    )
    return {
        "organization_id": user.organization_id,
        "fields": [
            {
                "dataset_name": row.dataset_name,
                "field_name": row.field_name,
                "data_type": row.data_type,
                "sensitivity": row.sensitivity,
                "description": row.description,
            }
            for row in rows
        ],
    }
