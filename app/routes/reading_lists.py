from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_login, templates
from app.models.reading_list import ReadingList, ReadingListItem

router = APIRouter(tags=["reading_lists"])


@router.get("/", response_class=HTMLResponse)
async def list_reading_lists(
    request: Request,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    lists = (
        db.query(ReadingList).order_by(ReadingList.created_at.desc()).all()
    )
    return templates.TemplateResponse(
        "reading_lists/list.html",
        {"request": request, "user": user, "reading_lists": lists},
    )


@router.get("/{list_id}", response_class=HTMLResponse)
async def reading_list_detail(
    request: Request,
    list_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    rl = (
        db.query(ReadingList)
        .options(joinedload(ReadingList.items).joinedload(ReadingListItem.article))
        .filter(ReadingList.id == list_id)
        .first()
    )
    if not rl:
        return templates.TemplateResponse(
            "404.html", {"request": request, "user": user}, status_code=404
        )

    # Group items by section
    sections: dict[str, list] = {}
    for item in sorted(rl.items, key=lambda i: (i.section, i.position)):
        sections.setdefault(item.section or "General", []).append(item)

    return templates.TemplateResponse(
        "reading_lists/detail.html",
        {
            "request": request,
            "user": user,
            "reading_list": rl,
            "sections": sections,
        },
    )


@router.get("/{list_id}/export", response_class=PlainTextResponse)
async def export_reading_list(
    list_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    rl = (
        db.query(ReadingList)
        .options(joinedload(ReadingList.items).joinedload(ReadingListItem.article))
        .filter(ReadingList.id == list_id)
        .first()
    )
    if not rl:
        return PlainTextResponse("Not found", status_code=404)

    lines = [f"# {rl.title}", ""]
    if rl.description:
        lines += [rl.description, ""]
    if rl.total_reading_time:
        lines.append(f"**Estimated reading time:** {rl.total_reading_time} minutes")
        lines.append("")

    sections: dict[str, list] = {}
    for item in sorted(rl.items, key=lambda i: (i.section, i.position)):
        sections.setdefault(item.section or "General", []).append(item)

    for section_name, items in sections.items():
        lines.append(f"## {section_name}")
        lines.append("")
        for item in items:
            a = item.article
            lines.append(f"- [{a.title}]({a.url})")
            if a.source:
                lines.append(f"  *Source: {a.source}*")
            if a.reading_time_minutes:
                lines.append(f"  *Reading time: {a.reading_time_minutes} min*")
            if item.notes:
                lines.append(f"  > {item.notes}")
            lines.append("")

    if rl.discussion_prompts:
        lines.append("## Discussion Prompts")
        lines.append("")
        for prompt in rl.discussion_prompts.split("\n"):
            prompt = prompt.strip()
            if prompt:
                lines.append(f"- {prompt}")
        lines.append("")

    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="reading-list-{list_id}.md"'},
    )


@router.post("/{list_id}/delete")
async def delete_reading_list(
    list_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    rl = db.query(ReadingList).filter(ReadingList.id == list_id).first()
    if rl:
        db.delete(rl)
        db.commit()
    return RedirectResponse("/reading-lists", status_code=303)
