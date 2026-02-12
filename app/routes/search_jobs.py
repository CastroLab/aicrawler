from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_login, templates
from app.models.search_job import SearchExecution, SearchJob

router = APIRouter(tags=["search_jobs"])


@router.get("/", response_class=HTMLResponse)
async def list_search_jobs(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    jobs = db.query(SearchJob).order_by(SearchJob.created_at.desc()).all()
    return templates.TemplateResponse(
        "search_jobs/list.html",
        {"request": request, "user": user, "jobs": jobs},
    )


@router.get("/add", response_class=HTMLResponse)
async def add_search_job_form(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse(
        "search_jobs/add.html", {"request": request, "user": user}
    )


@router.post("/add")
async def add_search_job(
    request: Request,
    name: str = Form(...),
    query: str = Form(...),
    schedule: str = Form("daily"),
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    job = SearchJob(name=name, query=query, schedule=schedule)
    db.add(job)
    db.commit()
    return RedirectResponse("/search-jobs", status_code=303)


@router.post("/{job_id}/toggle")
async def toggle_search_job(
    job_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if job:
        job.enabled = not job.enabled
        db.commit()
    return RedirectResponse("/search-jobs", status_code=303)


@router.post("/{job_id}/run")
async def run_search_job(
    request: Request,
    job_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        return RedirectResponse("/search-jobs", status_code=303)

    from app.services.discovery import run_search_job

    result = run_search_job(db, job)
    return RedirectResponse(f"/search-jobs/{job_id}/history", status_code=303)


@router.get("/{job_id}/history", response_class=HTMLResponse)
async def search_job_history(
    request: Request,
    job_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        return RedirectResponse("/search-jobs", status_code=303)
    executions = (
        db.query(SearchExecution)
        .filter(SearchExecution.search_job_id == job_id)
        .order_by(SearchExecution.started_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        "search_jobs/history.html",
        {"request": request, "user": user, "job": job, "executions": executions},
    )


@router.post("/{job_id}/delete")
async def delete_search_job(
    job_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if job:
        db.delete(job)
        db.commit()
    return RedirectResponse("/search-jobs", status_code=303)
