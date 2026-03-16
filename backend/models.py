"""Pydantic schemas for API request/response."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    status: str
    message: str
    result_filename: str | None = None


class MappingEntryResponse(BaseModel):
    ja_node_id: str
    en_node_id: str
    ja_text: str
    en_text: str
    score: float
    vector_score: float
    order_score: float
    low_conf: bool
