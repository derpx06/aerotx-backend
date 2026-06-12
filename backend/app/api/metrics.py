from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.observability.metrics import MetricsService

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(session: AsyncSession = Depends(get_session)) -> dict:
    return await MetricsService(session).snapshot()
