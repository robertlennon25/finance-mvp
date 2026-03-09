from __future__ import annotations

from document_pipeline.config import INBOX_ROOT
from worker_api.config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
    is_supabase_worker_configured,
)


def sync_deal_documents_from_supabase(deal_id: str) -> int:
    if not is_supabase_worker_configured():
        return 0

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - depends on env packages
        raise RuntimeError(
            "Supabase worker dependencies are not installed. Run pip install -r requirements.txt."
        ) from exc

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    inbox_dir = INBOX_ROOT / deal_id
    inbox_dir.mkdir(parents=True, exist_ok=True)

    response = (
        supabase.table("documents")
        .select("file_name,storage_bucket,storage_path")
        .eq("deal_id", deal_id)
        .execute()
    )
    rows = response.data or []
    synced = 0

    for row in rows:
        file_name = row["file_name"]
        bucket = row.get("storage_bucket") or SUPABASE_STORAGE_BUCKET
        storage_path = row["storage_path"]
        target_path = inbox_dir / file_name

        if target_path.exists():
            continue

        download = supabase.storage.from_(bucket).download(storage_path)
        target_path.write_bytes(download)
        synced += 1

    return synced
