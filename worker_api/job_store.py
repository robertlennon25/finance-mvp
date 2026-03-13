from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from worker_api.config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    WORKER_STATE_ROOT,
    ensure_worker_dirs,
    is_supabase_worker_configured,
)


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
    print(
        "[job_store] create_job",
        {
            "job_id": job_id,
            "deal_id": job.get("deal_id"),
            "phase": job.get("phase"),
            "status": job.get("status"),
            "progress": job.get("progress"),
        },
    )
    return job


def read_job(job_id: str) -> Dict[str, Any] | None:
    cloud_job = _read_from_supabase(job_id)
    if cloud_job:
        print(
            "[job_store] read_job from supabase",
            {
                "job_id": job_id,
                "status": cloud_job.get("status"),
                "progress": cloud_job.get("progress"),
                "updated_at": cloud_job.get("updated_at"),
            },
        )
        return cloud_job
    path = _path(job_id)
    if not path.exists():
        print(f"[job_store] read_job missing {job_id}")
        return None
    local_job = json.loads(path.read_text(encoding="utf-8"))
    print(
        "[job_store] read_job from local",
        {
            "job_id": job_id,
            "status": local_job.get("status"),
            "progress": local_job.get("progress"),
            "updated_at": local_job.get("updated_at"),
        },
    )
    return local_job


def update_job(job_id: str, **updates: Any) -> Dict[str, Any]:
    job = read_job(job_id)
    if not job:
        raise FileNotFoundError(f"Unknown job id: {job_id}")
    job.update(updates)
    job["updated_at"] = _now()
    _write(job_id, job)
    print(
        "[job_store] update_job",
        {
            "job_id": job_id,
            "status": job.get("status"),
            "progress": job.get("progress"),
            "message": job.get("message"),
            "updated_at": job.get("updated_at"),
        },
    )
    return job


def _write(job_id: str, payload: Dict[str, Any]) -> None:
    _path(job_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_to_supabase(payload)


def _path(job_id: str) -> Path:
    return WORKER_STATE_ROOT / f"{job_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_from_supabase(job_id: str) -> Dict[str, Any] | None:
    if not is_supabase_worker_configured():
        return None

    supabase = _get_supabase_client()
    if not supabase:
        return None

    response = (
        supabase.table("pipeline_runs")
        .select("job_id, deal_id, phase, status, progress, message, cached, triggered_by, owner_user_id, created_at, updated_at")
        .eq("job_id", job_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    return _normalize_supabase_row(rows[0])


def _write_to_supabase(payload: Dict[str, Any]) -> None:
    if not is_supabase_worker_configured():
        return

    supabase = _get_supabase_client()
    if not supabase:
        return

    db_payload = {
        "job_id": payload["job_id"],
        "deal_id": payload.get("deal_id"),
        "phase": payload.get("phase"),
        "status": payload.get("status", "queued"),
        "progress": int(payload.get("progress", 0) or 0),
        "message": payload.get("message"),
        "cached": bool(payload.get("cached", False)),
        "triggered_by": payload.get("triggered_by", "frontend"),
        "owner_user_id": payload.get("user_id"),
        "created_at": payload.get("created_at") or _now(),
        "updated_at": payload.get("updated_at") or _now(),
    }
    result = supabase.table("pipeline_runs").upsert(
        db_payload,
        on_conflict="job_id",
    ).execute()
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Failed to write worker job to Supabase: {error}")
    print(
        "[job_store] wrote job to supabase",
        {
            "job_id": db_payload.get("job_id"),
            "status": db_payload.get("status"),
            "progress": db_payload.get("progress"),
            "updated_at": db_payload.get("updated_at"),
        },
    )


def _normalize_supabase_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": row.get("job_id"),
        "deal_id": row.get("deal_id"),
        "phase": row.get("phase"),
        "status": row.get("status"),
        "progress": row.get("progress", 0),
        "message": row.get("message"),
        "cached": bool(row.get("cached", False)),
        "triggered_by": row.get("triggered_by", "frontend"),
        "user_id": row.get("owner_user_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _get_supabase_client():
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return None
    try:
        from supabase import create_client
    except ImportError:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
