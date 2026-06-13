import boto3
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
        "bedrock": _check_bedrock(),
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


def _check_bedrock() -> bool:
    """
    Verify that AWS credentials are resolvable and the Bedrock Runtime endpoint
    is reachable. Does NOT call invoke_model to avoid costs on health checks.
    """
    settings = get_settings()
    try:
        kwargs: dict = {"region_name": settings.aws_region}
        if settings.aws_access_key_id:
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        # list_foundation_models is free and confirms creds + endpoint reachability
        client = boto3.client("bedrock", **kwargs)
        client.list_foundation_models(byOutputModality="TEXT")
        return True
    except Exception:
        return False
