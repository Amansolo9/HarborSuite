from __future__ import annotations

from fastapi import APIRouter

from backend.api.routers import engagement_router, folio_router, governance_router, operations_router, orders_router

router = APIRouter(prefix="/api/v1", tags=["pms"])
router.include_router(operations_router)
router.include_router(orders_router)
router.include_router(folio_router)
router.include_router(engagement_router)
router.include_router(governance_router)
