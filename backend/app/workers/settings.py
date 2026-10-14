from __future__ import annotations

import structlog
from arq.connections import RedisSettings
from arq import cron

from app.config import settings
from app.workers.tasks.rag_tasks import index_topic_resources
from app.workers.tasks.mastery_tasks import apply_mastery_decay
from app.workers.tasks.analytics_tasks import refresh_concept_performance, update_concept_mastery_task

log = structlog.get_logger()


async def startup(ctx):
    log.info("🚀 Starting arq background worker process")


async def shutdown(ctx):
    log.info("👋 Shutting down arq background worker process")


class WorkerSettings:
    """arq worker configuration settings."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    
    # Task functions
    functions = [
        index_topic_resources,
        apply_mastery_decay,
        refresh_concept_performance,
        update_concept_mastery_task,
    ]
    
    # Scheduled / periodic jobs
    cron_jobs = [
        # Apply mastery decay daily at midnight
        cron(apply_mastery_decay, hour=0, minute=0),
        # Refresh materialized analytics views hourly
        cron(refresh_concept_performance, minute=0),
    ]
    
    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    
    # Tuning settings
    max_jobs = 10
    job_timeout = 300
    retry_jobs = True
    max_tries = 3
