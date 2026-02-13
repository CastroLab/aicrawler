import logging

from app.database import SessionLocal

logger = logging.getLogger(__name__)


def run_discovery():
    """Scheduled task: run all enabled search jobs."""
    db = SessionLocal()
    try:
        from app.services.discovery import run_all_search_jobs

        result = run_all_search_jobs(db)
        logger.info("Discovery complete: %s", result)
    except Exception:
        logger.exception("Discovery task failed")
    finally:
        db.close()


def run_fetching():
    """Scheduled task: fetch content for pending articles."""
    db = SessionLocal()
    try:
        from app.services.fetching import fetch_pending_articles

        result = fetch_pending_articles(db)
        logger.info("Fetching complete: %s", result)
    except Exception:
        logger.exception("Fetching task failed")
    finally:
        db.close()


def run_enrichment():
    """Scheduled task: enrich pending articles."""
    db = SessionLocal()
    try:
        from app.services.enrichment import enrich_pending_articles

        result = enrich_pending_articles(db)
        logger.info("Enrichment complete: %s", result)
    except Exception:
        logger.exception("Enrichment task failed")
    finally:
        db.close()


def run_weekly_digest():
    """Scheduled task: generate weekly digest."""
    db = SessionLocal()
    try:
        from app.services.digest import generate_weekly_digest

        result = generate_weekly_digest(db)
        logger.info("Weekly digest complete: %s", result)
    except Exception:
        logger.exception("Weekly digest task failed")
    finally:
        db.close()
