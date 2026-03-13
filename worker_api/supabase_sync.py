from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

import json

from document_pipeline.config import INBOX_ROOT, NORMALIZED_EXTRACTIONS_ROOT, OVERRIDES_ROOT, RESOLVED_EXTRACTIONS_ROOT
from worker_api.config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
    is_supabase_worker_configured,
)

DOWNLOAD_TIMEOUT_SECONDS = 60


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
    print(f"[supabase_sync] found {len(rows)} document rows for {deal_id}")

    for row in rows:
        file_name = row["file_name"]
        bucket = row.get("storage_bucket") or SUPABASE_STORAGE_BUCKET
        storage_path = row["storage_path"]
        target_path = inbox_dir / file_name

        if target_path.exists():
            print(f"[supabase_sync] skipping existing document {file_name} for {deal_id}")
            continue

        print(
            f"[supabase_sync] downloading document for {deal_id}: "
            f"bucket={bucket} path={storage_path} target={target_path.name}"
        )
        download = _download_with_timeout(
            lambda: supabase.storage.from_(bucket).download(storage_path),
            timeout_seconds=DOWNLOAD_TIMEOUT_SECONDS,
            label=f"document {storage_path}",
        )
        target_path.write_bytes(download)
        print(
            f"[supabase_sync] downloaded document for {deal_id}: "
            f"{target_path.name} ({len(download)} bytes)"
        )
        synced += 1

    return synced


def upload_deal_artifact(local_path: Path, storage_path: str, content_type: str) -> None:
    if not is_supabase_worker_configured() or not local_path.exists():
        return

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - depends on env packages
        raise RuntimeError(
            "Supabase worker dependencies are not installed. Run pip install -r requirements.txt."
        ) from exc

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    bucket = SUPABASE_STORAGE_BUCKET
    with local_path.open("rb") as file_obj:
        result = supabase.storage.from_(bucket).upload(
            storage_path,
            file_obj,
            {"content-type": content_type, "upsert": "true"},
        )
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Failed to upload artifact {local_path.name}: {error}")


def sync_deal_overrides_from_supabase(deal_id: str, user_id: str | None) -> int:
    if not is_supabase_worker_configured() or not user_id:
        return 0

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - depends on env packages
        raise RuntimeError(
            "Supabase worker dependencies are not installed. Run pip install -r requirements.txt."
        ) from exc

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    response = (
        supabase.table("user_overrides")
        .select("field_name,override_value")
        .eq("deal_id", deal_id)
        .eq("user_id", user_id)
        .execute()
    )
    rows = response.data or []
    overrides = {row["field_name"]: row["override_value"] for row in rows}

    OVERRIDES_ROOT.mkdir(parents=True, exist_ok=True)
    override_path = OVERRIDES_ROOT / f"{deal_id}_overrides.json"
    override_path.write_text(json.dumps(overrides, indent=2), encoding="utf-8")
    return len(overrides)


def sync_deal_artifacts_from_supabase(deal_id: str) -> int:
    if not is_supabase_worker_configured():
        return 0

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - depends on env packages
        raise RuntimeError(
            "Supabase worker dependencies are not installed. Run pip install -r requirements.txt."
        ) from exc

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    bucket = SUPABASE_STORAGE_BUCKET
    synced = 0

    artifact_targets = {
        f"{deal_id}_manifest.json": NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_manifest.json",
        f"{deal_id}_field_candidates.json": NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates.json",
        f"{deal_id}_field_candidates_normalized.json": NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates_normalized.json",
        f"{deal_id}_resolved.json": RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_resolved.json",
        f"{deal_id}_model_input.json": RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json",
        f"{deal_id}_review_payload.json": RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_review_payload.json",
    }

    for file_name, target_path in artifact_targets.items():
        storage_path = f"artifacts/{deal_id}/{file_name}"
        try:
            print(f"[supabase_sync] checking artifact {storage_path}")
            download = _download_with_timeout(
                lambda storage_path=storage_path: supabase.storage.from_(bucket).download(storage_path),
                timeout_seconds=DOWNLOAD_TIMEOUT_SECONDS,
                label=f"artifact {storage_path}",
            )
        except Exception:  # noqa: BLE001
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(download)
        print(
            f"[supabase_sync] synced artifact for {deal_id}: "
            f"{file_name} ({len(download)} bytes)"
        )
        synced += 1

    return synced


def _download_with_timeout(fetcher, timeout_seconds: int, label: str) -> bytes:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fetcher)
        try:
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            raise TimeoutError(
                f"Timed out after {timeout_seconds}s while downloading {label} from Supabase Storage."
            ) from exc

    if not isinstance(result, (bytes, bytearray)):
        raise RuntimeError(f"Unexpected download payload type for {label}: {type(result)!r}")

    return bytes(result)
