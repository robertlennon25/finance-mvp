from __future__ import annotations

from document_pipeline.services.local_pipeline import run_local_ingestion
from document_pipeline.services.openai_extraction import run_chunk_extraction
from document_pipeline.services.prepare_model_inputs import prepare_model_inputs_for_deal
from document_pipeline.services.resolve_fields import resolve_deal_fields
from run_build_workbook_from_deal import main as build_workbook_main
from worker_api.job_store import update_job
from worker_api.supabase_sync import sync_deal_documents_from_supabase


def run_pipeline_job(job_id: str, deal_id: str, phase: str, max_chunks: int | None) -> None:
    synced = sync_deal_documents_from_supabase(deal_id)
    update_job(
        job_id,
        status="running",
        progress=5,
        message=f"Synced {synced} document(s) from Supabase Storage",
    )

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

    if phase in {"analysis", "full"}:
        update_job(job_id, progress=75, message="Preparing model inputs")
        resolve_deal_fields(deal_id)
        prepare_model_inputs_for_deal(deal_id)

        update_job(job_id, progress=90, message="Building workbook")
        build_workbook_for_deal(deal_id)

    update_job(job_id, status="completed", progress=100, message="Completed")


def build_workbook_for_deal(deal_id: str) -> None:
    import sys

    original_argv = sys.argv[:]
    try:
        sys.argv = ["run_build_workbook_from_deal.py", deal_id]
        build_workbook_main()
    finally:
        sys.argv = original_argv
