from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_login, templates
from app.models.article import Article
from app.models.digest import Digest
from app.models.tag import Tag
from app.models.search_job import SearchJob
from app.models.reading_list import ReadingList

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(require_login), db: Session = Depends(get_db)):
    stats = {
        "total_articles": db.query(Article).count(),
        "pending_articles": db.query(Article).filter(Article.status == "pending").count(),
        "fetched_articles": db.query(Article).filter(Article.status == "fetched").count(),
        "enriched_articles": db.query(Article).filter(Article.status == "enriched").count(),
        "total_tags": db.query(Tag).count(),
        "search_jobs": db.query(SearchJob).filter(SearchJob.enabled == True).count(),
        "reading_lists": db.query(ReadingList).count(),
        "digests": db.query(Digest).count(),
    }

    latest_digest = (
        db.query(Digest)
        .filter(Digest.status == "completed")
        .order_by(Digest.created_at.desc())
        .first()
    )

    recent_articles = (
        db.query(Article)
        .order_by(Article.created_at.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "recent_articles": recent_articles,
            "latest_digest": latest_digest,
        },
    )
