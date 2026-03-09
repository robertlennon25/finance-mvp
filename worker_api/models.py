from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    deal_id: str = Field(min_length=1)
    phase: Literal["extract", "analysis", "full"] = "extract"
    max_chunks: Optional[int] = Field(default=5, ge=1, le=12)
    triggered_by: str = "frontend"
    user_id: Optional[str] = None


class PipelineRunResponse(BaseModel):
    ok: bool = True
    job_id: str
    status: str

