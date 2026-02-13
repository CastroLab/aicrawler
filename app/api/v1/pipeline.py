from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import require_api_token
from app.database import get_db
from app.models.article import Article
from app.schemas.content import PipelineStatusOut

router = APIRouter(dependencies=[Depends(require_api_token)])


@router.get("/status")
async def pipeline_status(db: Session = Depends(get_db)):
    """Get current pipeline status counts."""
    counts = {}
    for status in ["pending", "fetched", "fetch_failed", "enriched", "error"]:
        counts[status] = db.query(Article).filter(Article.status == status).count()

    return PipelineStatusOut(
        pending_articles=counts["pending"],
        fetched_articles=counts["fetched"],
        fetch_failed_articles=counts["fetch_failed"],
        enriched_articles=counts["enriched"],
        error_articles=counts["error"],
        total_articles=sum(counts.values()),
    )


@router.post("/discover")
async def trigger_discovery(db: Session = Depends(get_db)):
    """Run all enabled search jobs now."""
    from app.services.discovery import run_all_search_jobs

    result = run_all_search_jobs(db)
    return {"status": "completed", "results": result}


@router.post("/fetch")
async def trigger_fetch(db: Session = Depends(get_db)):
    """Fetch content for all pending articles."""
    from app.services.fetching import fetch_pending_articles

    result = fetch_pending_articles(db)
    return {"status": "completed", "results": result}


@router.post("/enrich")
async def trigger_enrich(db: Session = Depends(get_db)):
    """Enrich all fetched/fetch_failed articles."""
    from app.services.enrichment import enrich_pending_articles

    result = enrich_pending_articles(db)
    return {"status": "completed", "results": result}
