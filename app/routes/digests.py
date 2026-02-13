import datetime as dt

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_login, templates
from app.models.digest import Digest, DigestArticle, DigestSection

router = APIRouter(tags=["digests"])


@router.get("/", response_class=HTMLResponse)
async def list_digests(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    digests = (
        db.query(Digest)
        .order_by(Digest.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "digests/list.html",
        {"request": request, "user": user, "digests": digests},
    )


@router.get("/create", response_class=HTMLResponse)
async def create_digest_form(
    request: Request,
    user=Depends(require_login),
):
    today = dt.date.today()
    week_ago = today - dt.timedelta(days=7)
    return templates.TemplateResponse(
        "digests/create.html",
        {"request": request, "user": user, "default_start": week_ago, "default_end": today},
    )


@router.post("/create")
async def create_digest(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
    period_start: str = Form(...),
    period_end: str = Form(...),
):
    from app.services.digest import generate_digest

    start = dt.datetime.strptime(period_start, "%Y-%m-%d")
    end = dt.datetime.strptime(period_end, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59,
    )

    digest = generate_digest(db, start, end, digest_type="manual")
    if digest:
        return RedirectResponse(f"/digests/{digest.id}", status_code=303)
    return RedirectResponse("/digests", status_code=303)


@router.get("/{digest_id}", response_class=HTMLResponse)
async def view_digest(
    request: Request,
    digest_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    digest = (
        db.query(Digest)
        .options(
            joinedload(Digest.sections)
            .joinedload(DigestSection.articles)
            .joinedload(DigestArticle.article),
        )
        .filter(Digest.id == digest_id)
        .first()
    )
    if not digest:
        return templates.TemplateResponse(
            "404.html", {"request": request, "user": user}, status_code=404,
        )
    return templates.TemplateResponse(
        "digests/detail.html",
        {"request": request, "user": user, "digest": digest},
    )


@router.get("/{digest_id}/export")
async def export_digest(
    digest_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    if not digest or not digest.full_markdown:
        return RedirectResponse("/digests", status_code=303)
    return PlainTextResponse(
        digest.full_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="digest-{digest.id}.md"'},
    )


@router.post("/{digest_id}/delete")
async def delete_digest(
    digest_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    if digest:
        db.delete(digest)
        db.commit()
    return RedirectResponse("/digests", status_code=303)
