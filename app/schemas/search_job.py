import datetime as dt

from pydantic import BaseModel


class SearchJobCreate(BaseModel):
    name: str
    query: str
    schedule: str = "daily"
    enabled: bool = True


class SearchJobUpdate(BaseModel):
    name: str | None = None
    query: str | None = None
    schedule: str | None = None
    enabled: bool | None = None


class SearchExecutionOut(BaseModel):
    id: int
    search_job_id: int
    started_at: dt.datetime
    finished_at: dt.datetime | None
    status: str
    articles_found: int
    articles_new: int
    error_message: str | None

    model_config = {"from_attributes": True}
