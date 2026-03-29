from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import require_roles
from backend.core.database import get_db
from backend.models import Role, UserAccount
from backend.schemas.pms import (
    AuditEventResponse,
    DataDictionaryExportResponse,
    DatasetVersionRequest,
    DatasetVersionResponse,
    ExportRequest,
    ExportResponse,
    LineageRequest,
    LineageResponse,
    MetricDefinitionRequest,
    MetricDefinitionResponse,
)
from backend.services.exports import create_export
from backend.services.governance import create_metric_definition, export_dictionary, list_lineage, register_dataset_version, register_lineage
from backend.services.overview import list_audit_events

router = APIRouter(tags=["pms"])


def _page(items: list, limit: int, offset: int) -> list:
    return items[offset : offset + limit]


@router.post("/exports", response_model=ExportResponse)
def create_export_route(
    payload: ExportRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> ExportResponse:
    try:
        export = create_export(db, user, payload.export_type, payload.scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExportResponse(
        export_id=export.id,
        export_type=export.export_type,
        storage_path=export.storage_path,
        checksum=export.checksum,
    )


@router.get("/audit/logs", response_model=list[AuditEventResponse])
def audit_logs(
    sort: str = Query(default="created_desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(require_roles(Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> list[AuditEventResponse]:
    rows = list_audit_events(db, user)
    if sort == "created_asc":
        rows = sorted(rows, key=lambda event: event.created_at)
    elif sort == "created_desc":
        rows = sorted(rows, key=lambda event: event.created_at, reverse=True)
    else:
        raise HTTPException(status_code=400, detail="Unsupported sort option.")
    events = _page(rows, limit, offset)
    return [
        AuditEventResponse(
            id=event.id,
            actor=event.actor,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            organization_id=event.organization_id,
            created_at=event.created_at,
            metadata=json.loads(event.metadata_json),
        )
        for event in events
    ]


@router.post("/governance/metrics", response_model=MetricDefinitionResponse)
def create_metric_route(
    payload: MetricDefinitionRequest,
    user: UserAccount = Depends(require_roles(Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> MetricDefinitionResponse:
    row = create_metric_definition(db, user, payload.metric_name, payload.description, payload.source_query_ref, payload.version)
    return MetricDefinitionResponse(
        id=row.id,
        metric_name=row.metric_name,
        description=row.description,
        source_query_ref=row.source_query_ref,
        version=row.version,
    )


@router.post("/governance/datasets", response_model=DatasetVersionResponse)
def create_dataset_route(
    payload: DatasetVersionRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> DatasetVersionResponse:
    row = register_dataset_version(db, user, payload.dataset_name, payload.version, payload.dataset_schema)
    return DatasetVersionResponse(id=row.id, dataset_name=row.dataset_name, version=row.version, checksum=row.checksum)


@router.post("/governance/lineage", response_model=LineageResponse)
def create_lineage_route(
    payload: LineageRequest,
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> LineageResponse:
    try:
        row = register_lineage(db, user, payload.metric_name, payload.dataset_version_id, payload.source_tables, payload.source_query_ref)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LineageResponse(
        id=row.id,
        metric_name=row.metric_name,
        dataset_version_id=row.dataset_version_id,
        source_tables=[part for part in row.source_tables.split(",") if part],
        source_query_ref=row.source_query_ref,
    )


@router.get("/governance/lineage", response_model=list[LineageResponse])
def list_lineage_route(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER)),
    db: Session = Depends(get_db),
) -> list[LineageResponse]:
    return [
        LineageResponse(
            id=row.id,
            metric_name=row.metric_name,
            dataset_version_id=row.dataset_version_id,
            source_tables=[part for part in row.source_tables.split(",") if part],
            source_query_ref=row.source_query_ref,
        )
        for row in _page(list_lineage(db, user), limit, offset)
    ]


@router.get("/governance/dictionary/export", response_model=DataDictionaryExportResponse)
def export_dictionary_route(
    user: UserAccount = Depends(require_roles(Role.FINANCE, Role.GENERAL_MANAGER, Role.CONTENT_EDITOR)),
    db: Session = Depends(get_db),
) -> DataDictionaryExportResponse:
    return DataDictionaryExportResponse(**export_dictionary(db, user))
