import logging

logger = logging.getLogger(__name__)


def register_jobs(scheduler, settings):
    """Register scheduled jobs. Called during startup."""
    from app.scheduler.tasks import run_discovery, run_enrichment

    scheduler.add_job(
        run_discovery,
        "cron",
        hour=settings.DISCOVERY_CRON_HOUR,
        id="discovery",
        replace_existing=True,
    )

    scheduler.add_job(
        run_enrichment,
        "interval",
        hours=settings.ENRICHMENT_INTERVAL_HOURS,
        id="enrichment",
        replace_existing=True,
    )

    logger.info(
        "Jobs registered: discovery at hour=%s, enrichment every %sh",
        settings.DISCOVERY_CRON_HOUR,
        settings.ENRICHMENT_INTERVAL_HOURS,
    )
