import datetime as dt

from pydantic import BaseModel


class ArticleContentOut(BaseModel):
    article_id: int
    full_text: str | None
    content_hash: str | None
    fetch_status: str
    fetch_error: str | None
    http_status: int | None
    extracted_title: str | None
    extracted_author: str | None
    extracted_date: str | None
    word_count: int | None
    fetched_at: dt.datetime | None

    model_config = {"from_attributes": True}


class DigestCreate(BaseModel):
    period_start: dt.datetime
    period_end: dt.datetime
    digest_type: str = "manual"


class DigestSectionOut(BaseModel):
    id: int
    title: str
    section_type: str
    content_markdown: str | None
    position: int

    model_config = {"from_attributes": True}


class DigestOut(BaseModel):
    id: int
    title: str
    digest_type: str
    status: str
    period_start: dt.datetime | None
    period_end: dt.datetime | None
    executive_summary: str | None
    trend_analysis: str | None
    article_count: int
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class DigestDetailOut(DigestOut):
    full_markdown: str | None
    sections: list[DigestSectionOut] = []


class PipelineStatusOut(BaseModel):
    pending_articles: int
    fetched_articles: int
    fetch_failed_articles: int
    enriched_articles: int
    error_articles: int
    total_articles: int
