"""
InfraGuard AI — Admin Analytics & Survey History Router

Provides real-time administrative analytics endpoints for the Admin Dashboard:
    - Real-time total inspections, defect counts, high-risk flags, pending reviews
    - Dynamic damage distribution (pie chart)
    - Dynamic severity distribution (bar chart)
    - Full inspection logs with GPS, weather, and municipal maintenance status
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from backend.services.inspection_store import inspection_store

logger = logging.getLogger("infraguard.router.admin")

router = APIRouter(prefix="/admin", tags=["Admin Analytics"])


@router.get(
    "/analytics",
    summary="Get live admin dashboard analytics",
    description="Returns real-time aggregated metrics from all field inspections.",
)
async def get_analytics() -> dict[str, Any]:
    """Retrieve real-time metrics, defect distributions, and recent inspections."""
    return inspection_store.get_analytics()


@router.get(
    "/inspections",
    summary="List all recorded inspections",
    description="Returns the full chronological inspection log.",
)
async def get_inspections(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve list of recent inspections."""
    return inspection_store.get_all(limit=limit)
