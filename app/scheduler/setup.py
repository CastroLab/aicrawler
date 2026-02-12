import logging

logger = logging.getLogger(__name__)


def start_scheduler():
    """Initialize and start APScheduler. Returns scheduler instance or None."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.config import get_settings

        settings = get_settings()
        scheduler = BackgroundScheduler()

        # Jobs registered in Phase 5
        from app.scheduler.jobs import register_jobs

        register_jobs(scheduler, settings)
        scheduler.start()
        logger.info("Scheduler started")
        return scheduler
    except Exception as e:
        logger.warning("Scheduler not started: %s", e)
        return None
