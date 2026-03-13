from __future__ import annotations

from pathlib import Path

import json

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, OVERRIDES_ROOT, RESOLVED_EXTRACTIONS_ROOT
from document_pipeline.services.local_pipeline import run_local_ingestion
from document_pipeline.services.openai_extraction import run_chunk_extraction
from document_pipeline.services.prepare_model_inputs import prepare_model_inputs_for_deal
from document_pipeline.services.resolve_fields import resolve_deal_fields
from run_build_workbook_from_deal import main as build_workbook_main
from worker_api.job_store import update_job
from worker_api.supabase_sync import (
    sync_deal_artifacts_from_supabase,
    sync_deal_documents_from_supabase,
    sync_deal_overrides_from_supabase,
    upload_deal_artifact,
)


def run_pipeline_job(job_id: str, deal_id: str, phase: str, max_chunks: int | None, user_id: str | None = None) -> None:
    print(
        "[worker_pipeline] job start",
        json.dumps(
            {
                "job_id": job_id,
                "deal_id": deal_id,
                "phase": phase,
                "user_id": user_id,
            }
        ),
    )
    print(f"[worker_pipeline] syncing documents for {deal_id}")
    synced = sync_deal_documents_from_supabase(deal_id)
    print(f"[worker_pipeline] synced {synced} documents for {deal_id}")
    print(f"[worker_pipeline] syncing prior artifacts for {deal_id}")
    artifact_sync_count = sync_deal_artifacts_from_supabase(deal_id)
    print(f"[worker_pipeline] synced {artifact_sync_count} prior artifacts for {deal_id}")
    update_job(
        job_id,
        status="running",
        progress=5,
        message=f"Synced {synced} document(s) and {artifact_sync_count} artifact(s) from Supabase Storage",
    )
    override_count = sync_deal_overrides_from_supabase(deal_id, user_id)
    override_path = OVERRIDES_ROOT / f"{deal_id}_overrides.json"
    if override_path.exists():
        override_payload = json.loads(override_path.read_text(encoding="utf-8"))
        print(
            "[worker_pipeline] synced overrides",
            json.dumps(
                {
                    "deal_id": deal_id,
                    "override_count": override_count,
                    "override_revenue": override_payload.get("revenue"),
                }
            ),
        )
    if override_count:
        update_job(job_id, progress=10, message=f"Synced {override_count} override(s)")

    if phase in {"extract", "full"}:
        print(f"[worker_pipeline] entering extract phase for {deal_id}")
        update_job(job_id, progress=15, message="Reading inputs")
        print(f"[worker_pipeline] calling run_local_ingestion for {deal_id}")
        run_local_ingestion(deal_id)
        print(f"[worker_pipeline] completed run_local_ingestion for {deal_id}")

        update_job(job_id, progress=40, message="Extracting with GPT-4.1 mini")
        print(f"[worker_pipeline] calling run_chunk_extraction for {deal_id}")
        extraction_result = run_chunk_extraction(deal_id=deal_id, max_chunks=max_chunks)
        print(
            "[worker_pipeline] completed run_chunk_extraction",
            json.dumps(
                {
                    "deal_id": deal_id,
                    "candidate_count": extraction_result.get("candidate_count"),
                    "cached": extraction_result.get("cached"),
                }
            ),
        )

        update_job(
            job_id,
            progress=60,
            message="Resolving extracted fields",
            cached=bool(extraction_result.get("cached", False)),
        )
        print(f"[worker_pipeline] calling resolve_deal_fields for {deal_id}")
        resolve_deal_fields(deal_id)
        print(f"[worker_pipeline] calling prepare_model_inputs_for_deal for {deal_id}")
        prepare_model_inputs_for_deal(deal_id)
        print(f"[worker_pipeline] uploading review artifacts for {deal_id}")
        upload_review_artifacts(deal_id)

    if phase in {"analysis", "full"}:
        update_job(job_id, progress=75, message="Preparing model inputs")
        if _has_prepared_model_input(deal_id):
            print(f"[worker_pipeline] using prepared model input for {deal_id}")
            _apply_overrides_to_existing_model_input(deal_id)
        elif _has_field_candidates(deal_id):
            print(f"[worker_pipeline] rebuilding model input from candidates for {deal_id}")
            resolve_deal_fields(deal_id)
            prepare_model_inputs_for_deal(deal_id)
            _apply_overrides_to_existing_model_input(deal_id)
        else:
            raise FileNotFoundError(
                f"No prepared model input or candidates found for analysis run: {deal_id}"
            )
        model_input_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json"
        if model_input_path.exists():
            model_input_payload = json.loads(model_input_path.read_text(encoding="utf-8"))
            print(
                "[worker_pipeline] model input before build",
                json.dumps(
                    {
                        "deal_id": deal_id,
                        "revenue": model_input_payload.get("revenue"),
                        "entry_multiple": model_input_payload.get("entry_multiple"),
                    }
                ),
            )
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


def _has_field_candidates(deal_id: str) -> bool:
    return (NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates.json").exists()


def _has_prepared_model_input(deal_id: str) -> bool:
    return (RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json").exists()


def _apply_overrides_to_existing_model_input(deal_id: str) -> None:
    model_input_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json"
    review_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_review_payload.json"
    override_path = OVERRIDES_ROOT / f"{deal_id}_overrides.json"

    if not model_input_path.exists():
        raise FileNotFoundError(
            f"Candidates file not found and no prepared model input exists: {model_input_path}"
        )

    model_input = json.loads(model_input_path.read_text(encoding="utf-8"))
    overrides = (
        json.loads(override_path.read_text(encoding="utf-8"))
        if override_path.exists()
        else {}
    )

    for field_name, value in overrides.items():
        model_input[field_name] = value

    print(
        "[worker_pipeline] apply overrides to model input",
        json.dumps(
            {
                "deal_id": deal_id,
                "override_revenue": overrides.get("revenue"),
                "resulting_revenue": model_input.get("revenue"),
            }
        ),
    )

    model_input_path.write_text(json.dumps(model_input, indent=2), encoding="utf-8")

    if review_path.exists():
        review_payload = json.loads(review_path.read_text(encoding="utf-8"))
        for field_name, value in overrides.items():
            field_state = review_payload.setdefault("fields", {}).setdefault(
                field_name,
                {
                    "selected": {},
                    "options": [],
                    "warnings": [],
                    "recommended_estimate": None,
                },
            )
            field_state["selected"] = {
                "value": value,
                "confidence": 1.0,
                "source_document_id": None,
                "source_locator": "user_override",
                "method": "user_override",
                "notes": "Applied from saved override.",
                "source_urls": [],
            }
        review_path.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
