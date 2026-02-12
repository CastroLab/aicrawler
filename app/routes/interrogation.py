import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_login, templates
from app.models.query_log import InterrogationLog

router = APIRouter(tags=["interrogation"])


@router.get("/", response_class=HTMLResponse)
async def interrogation_page(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    recent_queries = (
        db.query(InterrogationLog)
        .order_by(InterrogationLog.created_at.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        "interrogation/query.html",
        {"request": request, "user": user, "recent_queries": recent_queries},
    )


@router.post("/query")
async def run_query(
    request: Request,
    query: str = Form(...),
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    from app.services.interrogation import process_query

    result = process_query(db, query, user_id=user["id"])

    return templates.TemplateResponse(
        "interrogation/result.html",
        {"request": request, "user": user, "query": query, "result": result},
    )


@router.get("/history", response_class=HTMLResponse)
async def query_history(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    queries = (
        db.query(InterrogationLog)
        .order_by(InterrogationLog.created_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        "interrogation/history.html",
        {"request": request, "user": user, "queries": queries},
    )
