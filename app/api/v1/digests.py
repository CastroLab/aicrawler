from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.api.v1.auth import require_api_token
from app.database import get_db
from app.models.digest import Digest, DigestSection
from app.schemas.content import DigestCreate, DigestDetailOut, DigestOut

router = APIRouter(dependencies=[Depends(require_api_token)])


@router.get("")
async def list_digests(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all digests."""
    total = db.query(Digest).count()
    digests = (
        db.query(Digest)
        .order_by(Digest.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [DigestOut.model_validate(d) for d in digests],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", status_code=201)
async def create_digest(
    data: DigestCreate,
    db: Session = Depends(get_db),
):
    """Generate a new digest for the given time range."""
    from app.services.digest import generate_digest

    digest = generate_digest(
        db,
        period_start=data.period_start,
        period_end=data.period_end,
        digest_type=data.digest_type,
    )
    if not digest:
        raise HTTPException(status_code=500, detail="Digest generation failed")
    return DigestDetailOut.model_validate(digest)


@router.get("/{digest_id}")
async def get_digest(
    digest_id: int,
    db: Session = Depends(get_db),
):
    """Get a single digest with sections."""
    digest = (
        db.query(Digest)
        .options(
            joinedload(Digest.sections).joinedload(DigestSection.articles),
        )
        .filter(Digest.id == digest_id)
        .first()
    )
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return DigestDetailOut.model_validate(digest)


@router.delete("/{digest_id}", status_code=204)
async def delete_digest(
    digest_id: int,
    db: Session = Depends(get_db),
):
    """Delete a digest."""
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    db.delete(digest)
    db.commit()


@router.get("/{digest_id}/markdown")
async def get_digest_markdown(
    digest_id: int,
    db: Session = Depends(get_db),
):
    """Get the full markdown rendering of a digest."""
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    if not digest.full_markdown:
        raise HTTPException(status_code=404, detail="Digest markdown not yet generated")
    return PlainTextResponse(
        digest.full_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="digest-{digest.id}.md"'},
    )
