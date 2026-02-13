from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin, templates
from app.models.article import Article
from app.models.search_job import SearchExecution

router = APIRouter(tags=["admin"])


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    recent_executions = (
        db.query(SearchExecution)
        .order_by(SearchExecution.started_at.desc())
        .limit(20)
        .all()
    )
    pending_count = db.query(Article).filter(Article.status == "pending").count()
    enrichable_count = (
        db.query(Article)
        .filter(Article.status.in_(["fetched", "fetch_failed"]))
        .count()
    )
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "recent_executions": recent_executions,
            "pending_count": pending_count,
            "enrichable_count": enrichable_count,
        },
    )


@router.post("/fetch-now")
async def fetch_now(
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.fetching import fetch_pending_articles

    result = fetch_pending_articles(db)
    return RedirectResponse("/admin", status_code=303)


@router.post("/enrich-now")
async def enrich_now(
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.enrichment import enrich_pending_articles

    result = enrich_pending_articles(db)
    return RedirectResponse("/admin", status_code=303)


@router.post("/discover-now")
async def discover_now(
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.discovery import run_all_search_jobs

    result = run_all_search_jobs(db)
    return RedirectResponse("/admin", status_code=303)
