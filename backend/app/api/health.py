import httpx
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    return await ready(session)


@router.get("/health/live")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    checks = {
        "postgresql": await _check_postgresql(session),
        "redis": await _check_redis(),
        "workers": _check_workers(),
        "gemini": await _check_gemini(),
    }
    status = "ok" if checks["postgresql"] and checks["redis"] else "degraded"
    return {"status": status, "checks": checks}


async def _check_postgresql(session: AsyncSession) -> bool:
    await session.execute(text("select 1"))
    return True


async def _check_redis() -> bool:
    redis = Redis.from_url(get_settings().redis_url)
    try:
        return bool(await redis.ping())
    except Exception:
        return False
    finally:
        await redis.aclose()


def _check_workers() -> bool:
    try:
        response = celery_app.control.ping(timeout=0.5)
        return bool(response)
    except Exception:
        return False


async def _check_gemini() -> bool:
    settings = get_settings()
    if not settings.gemini_api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("https://generativelanguage.googleapis.com")
        return response.status_code < 500
    except httpx.HTTPError:
        return False
