"""API router aggregation.

Combines all endpoint routers into a single API router.
Routes:
- /health - Health check endpoints
- /import - Data import endpoints
- /dashboard - Dashboard data endpoints
- /batch - Batch processing endpoints
- /analysis - Analysis results endpoints
- /reports - Report generation endpoints
- /agents - AI agent endpoints
- /journals - Journal entry search endpoints
- /settings - Application settings endpoints
"""

from fastapi import APIRouter

from app.api.endpoints import (
    agents,
    analysis,
    batch,
    dashboard,
    health,
    import_data,
    journals,
    reports,
    settings,
)

router = APIRouter()

# Include endpoint routers
router.include_router(
    health.router,
    tags=["Health"],
)
router.include_router(
    import_data.router,
    prefix="/import",
    tags=["Import"],
)
router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
router.include_router(
    batch.router,
    prefix="/batch",
    tags=["Batch Processing"],
)
router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"],
)
router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)
router.include_router(
    agents.router,
    prefix="/agents",
    tags=["AI Agents"],
)
router.include_router(
    journals.router,
    prefix="/journals",
    tags=["Journals"],
)
router.include_router(
    settings.router,
    prefix="/settings",
    tags=["Settings"],
)
