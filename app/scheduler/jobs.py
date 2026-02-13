import logging

logger = logging.getLogger(__name__)


def register_jobs(scheduler, settings):
    """Register scheduled jobs. Called during startup."""
    from app.scheduler.tasks import (
        run_discovery,
        run_enrichment,
        run_fetching,
        run_weekly_digest,
    )

    scheduler.add_job(
        run_discovery,
        "cron",
        hour=settings.DISCOVERY_CRON_HOUR,
        id="discovery",
        replace_existing=True,
    )

    scheduler.add_job(
        run_fetching,
        "interval",
        hours=settings.FETCHING_INTERVAL_HOURS,
        id="fetching",
        replace_existing=True,
    )

    scheduler.add_job(
        run_enrichment,
        "interval",
        hours=settings.ENRICHMENT_INTERVAL_HOURS,
        id="enrichment",
        replace_existing=True,
    )

    scheduler.add_job(
        run_weekly_digest,
        "cron",
        day_of_week=settings.DIGEST_CRON_DAY,
        hour=settings.DIGEST_CRON_HOUR,
        id="weekly_digest",
        replace_existing=True,
    )

    logger.info(
        "Jobs registered: discovery at hour=%s, fetching every %sh, "
        "enrichment every %sh, weekly digest on %s at %s",
        settings.DISCOVERY_CRON_HOUR,
        settings.FETCHING_INTERVAL_HOURS,
        settings.ENRICHMENT_INTERVAL_HOURS,
        settings.DIGEST_CRON_DAY,
        settings.DIGEST_CRON_HOUR,
    )
