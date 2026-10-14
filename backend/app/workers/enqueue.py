from __future__ import annotations

import structlog
try:
    from arq import create_pool
    from arq.connections import RedisSettings
except ImportError:
    create_pool = None
    RedisSettings = None
from app.config import settings

log = structlog.get_logger()


async def enqueue(job_name: str, *args, **kwargs) -> None:
    """
    Enqueue a background job to Redis using arq.
    This replaces FastAPI BackgroundTasks for reliable persistence, timeout, and retries.
    """
    if create_pool is None or RedisSettings is None:
        log.warning("arq not installed; skipping background job", job_name=job_name)
        return
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis.enqueue_job(job_name, *args, **kwargs)
        log.info("Job enqueued successfully", job_name=job_name, args=args, kwargs=kwargs)
    except Exception as exc:
        log.error("Failed to enqueue job", job_name=job_name, error=str(exc))
        raise
