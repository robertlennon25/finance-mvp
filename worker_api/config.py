from __future__ import annotations

import os
from pathlib import Path

from document_pipeline.config import INBOX_ROOT, PIPELINE_STATE_ROOT
from document_pipeline.storage.env import load_local_env


load_local_env()

WORKER_STATE_ROOT = PIPELINE_STATE_ROOT / "worker_jobs"
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "deal-documents")
WORKER_SHARED_SECRET = os.getenv("WORKER_SHARED_SECRET", "")


def ensure_worker_dirs() -> None:
    WORKER_STATE_ROOT.mkdir(parents=True, exist_ok=True)
    INBOX_ROOT.mkdir(parents=True, exist_ok=True)


def is_supabase_worker_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
