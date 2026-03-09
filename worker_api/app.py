from __future__ import annotations

import uuid

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from worker_api.config import WORKER_SHARED_SECRET, ensure_worker_dirs
from worker_api.job_store import create_job, read_job, update_job
from worker_api.models import PipelineRunRequest, PipelineRunResponse
from worker_api.pipeline import run_pipeline_job

app = FastAPI(title="Finance AI Worker", version="0.1.0")
ensure_worker_dirs()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pipeline/run", response_model=PipelineRunResponse)
def create_pipeline_run(
    payload: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> PipelineRunResponse:
    _enforce_shared_secret(authorization)

    job_id = str(uuid.uuid4())
    create_job(
        job_id,
        {
            "deal_id": payload.deal_id,
            "phase": payload.phase,
            "max_chunks": payload.max_chunks,
            "triggered_by": payload.triggered_by,
            "user_id": payload.user_id,
            "cached": False,
        },
    )
    background_tasks.add_task(
        _run_job_safe,
        job_id,
        payload.deal_id,
        payload.phase,
        payload.max_chunks,
        payload.user_id,
    )
    return PipelineRunResponse(job_id=job_id, status="queued")


@app.get("/pipeline/run/{job_id}")
def get_pipeline_run(job_id: str, authorization: str | None = Header(default=None)) -> dict:
    _enforce_shared_secret(authorization)

    job = read_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _run_job_safe(
    job_id: str,
    deal_id: str,
    phase: str,
    max_chunks: int | None,
    user_id: str | None,
) -> None:
    try:
        run_pipeline_job(job_id, deal_id, phase, max_chunks, user_id)
    except Exception as exc:  # noqa: BLE001
        update_job(job_id, status="failed", message=str(exc))


def _enforce_shared_secret(authorization: str | None) -> None:
    if not WORKER_SHARED_SECRET:
        return
    expected = f"Bearer {WORKER_SHARED_SECRET}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
