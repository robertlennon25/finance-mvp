from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from worker_api.config import WORKER_STATE_ROOT, ensure_worker_dirs


def create_job(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_worker_dirs()
    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Queued",
        "created_at": _now(),
        "updated_at": _now(),
        **payload,
    }
    _write(job_id, job)
    return job


def read_job(job_id: str) -> Dict[str, Any] | None:
    path = _path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def update_job(job_id: str, **updates: Any) -> Dict[str, Any]:
    job = read_job(job_id)
    if not job:
        raise FileNotFoundError(f"Unknown job id: {job_id}")
    job.update(updates)
    job["updated_at"] = _now()
    _write(job_id, job)
    return job


def _write(job_id: str, payload: Dict[str, Any]) -> None:
    _path(job_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _path(job_id: str) -> Path:
    return WORKER_STATE_ROOT / f"{job_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
