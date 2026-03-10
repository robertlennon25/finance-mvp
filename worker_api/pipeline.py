from __future__ import annotations

from pathlib import Path

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, RESOLVED_EXTRACTIONS_ROOT
from document_pipeline.services.local_pipeline import run_local_ingestion
from document_pipeline.services.openai_extraction import run_chunk_extraction
from document_pipeline.services.prepare_model_inputs import prepare_model_inputs_for_deal
from document_pipeline.services.resolve_fields import resolve_deal_fields
from run_build_workbook_from_deal import main as build_workbook_main
from worker_api.job_store import update_job
from worker_api.supabase_sync import (
    sync_deal_documents_from_supabase,
    sync_deal_overrides_from_supabase,
    upload_deal_artifact,
)


def run_pipeline_job(job_id: str, deal_id: str, phase: str, max_chunks: int | None, user_id: str | None = None) -> None:
    synced = sync_deal_documents_from_supabase(deal_id)
    update_job(
        job_id,
        status="running",
        progress=5,
        message=f"Synced {synced} document(s) from Supabase Storage",
    )
    override_count = sync_deal_overrides_from_supabase(deal_id, user_id)
    if override_count:
        update_job(job_id, progress=10, message=f"Synced {override_count} override(s)")

    if phase in {"extract", "full"}:
        update_job(job_id, progress=15, message="Reading inputs")
        run_local_ingestion(deal_id)

        update_job(job_id, progress=40, message="Extracting with GPT-4.1 mini")
        extraction_result = run_chunk_extraction(deal_id=deal_id, max_chunks=max_chunks)

        update_job(
            job_id,
            progress=60,
            message="Resolving extracted fields",
            cached=bool(extraction_result.get("cached", False)),
        )
        resolve_deal_fields(deal_id)
        prepare_model_inputs_for_deal(deal_id)
        upload_review_artifacts(deal_id)

    if phase in {"analysis", "full"}:
        update_job(job_id, progress=75, message="Preparing model inputs")
        resolve_deal_fields(deal_id)
        prepare_model_inputs_for_deal(deal_id)
        upload_review_artifacts(deal_id)

        update_job(job_id, progress=90, message="Building workbook")
        build_workbook_for_deal(deal_id)
        upload_workbook_artifacts(deal_id)

    update_job(job_id, status="completed", progress=100, message="Completed")


def build_workbook_for_deal(deal_id: str) -> None:
    import sys

    original_argv = sys.argv[:]
    try:
        sys.argv = ["run_build_workbook_from_deal.py", deal_id]
        build_workbook_main()
    finally:
        sys.argv = original_argv


def upload_review_artifacts(deal_id: str) -> None:
    review_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_review_payload.json"
    model_input_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json"
    manifest_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_manifest.json"

    upload_deal_artifact(review_path, _artifact_storage_path(deal_id, review_path.name), "application/json")
    upload_deal_artifact(model_input_path, _artifact_storage_path(deal_id, model_input_path.name), "application/json")
    upload_deal_artifact(manifest_path, _artifact_storage_path(deal_id, manifest_path.name), "application/json")


def upload_workbook_artifacts(deal_id: str) -> None:
    outputs_root = Path("outputs")
    workbook_path = outputs_root / f"{deal_id}_valuation_model.xlsx"
    summary_path = outputs_root / f"{deal_id}_summary.json"
    diagnostics_path = outputs_root / f"{deal_id}_diagnostics.json"

    upload_deal_artifact(
        workbook_path,
        _artifact_storage_path(deal_id, workbook_path.name),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    upload_deal_artifact(summary_path, _artifact_storage_path(deal_id, summary_path.name), "application/json")
    upload_deal_artifact(diagnostics_path, _artifact_storage_path(deal_id, diagnostics_path.name), "application/json")


def _artifact_storage_path(deal_id: str, file_name: str) -> str:
    return f"artifacts/{deal_id}/{file_name}"
