import { promises as fs } from "fs";
import path from "path";
import { execFile } from "child_process";
import crypto from "crypto";
import { promisify } from "util";

import { getSupabaseServiceRoleClient } from "@/lib/supabase/service-role";
import { getStaticCuratedExampleDealIds } from "@/lib/example-deals";
import {
  getRailwayWorkerUrl,
  getSupabaseStorageBucket,
  getWorkerSharedSecret,
} from "@/lib/supabase/config";

const execFileAsync = promisify(execFile);

const REPO_ROOT = path.resolve(process.cwd(), "..");
const RESOLVED_ROOT = path.join(REPO_ROOT, "data", "extractions", "resolved");
const NORMALIZED_ROOT = path.join(REPO_ROOT, "data", "extractions", "normalized");
const OVERRIDES_ROOT = path.join(REPO_ROOT, "data", "extractions", "overrides");
const OUTPUTS_ROOT = path.join(REPO_ROOT, "outputs");
const INBOX_ROOT = path.join(REPO_ROOT, "data", "documents", "inbox");
const PROCESSED_ROOT = path.join(REPO_ROOT, "data", "documents", "processed");
const PIPELINE_STATE_ROOT = path.join(REPO_ROOT, "data", "pipeline_state");
const DEAL_METADATA_ROOT = path.join(PIPELINE_STATE_ROOT, "deals");
const PIPELINE_RUNS_ROOT = path.join(PIPELINE_STATE_ROOT, "runs");

export async function getAvailableDeals() {
  const dealIds = await getAllDealIds();
  const deals = await Promise.all(dealIds.map((dealId) => getDealDetail(dealId)));

  return deals.filter(Boolean).sort((a, b) => a.dealId.localeCompare(b.dealId));
}

export async function getExampleDeals() {
  const curatedIds = await getCuratedExampleDealIds();
  const deals = await Promise.all(curatedIds.map((dealId) => getDealDetail(dealId)));
  return deals.filter(Boolean).sort((a, b) => a.dealId.localeCompare(b.dealId));
}

export async function getDealDetail(dealId, user = null) {
  const reviewPath = path.join(RESOLVED_ROOT, `${dealId}_review_payload.json`);
  const manifestPath = path.join(NORMALIZED_ROOT, `${dealId}_manifest.json`);
  const extractionMetadata = await getExtractionMetadata(dealId);
  const runHistory = await getDealRunHistory(dealId);
  const meta = await getDealMeta(dealId);
  const workbookPath = await getWorkbookPath(dealId);
  const workbookExistsInCloud = await hasSupabaseArtifact(dealId, `${dealId}_valuation_model.xlsx`);
  const workbookSummary = await getWorkbookSummary(dealId);
  const documents = await getDealDocuments(dealId);
  const reviewExists = (await exists(reviewPath)) || Boolean(await getSupabaseArtifactJson(dealId, `${dealId}_review_payload.json`));
  const manifest = (await exists(manifestPath))
    ? JSON.parse(await fs.readFile(manifestPath, "utf-8"))
    : (await getSupabaseArtifactJson(dealId, `${dealId}_manifest.json`)) ?? { document_count: documents.length, documents: [] };

  if (!documents.length && !reviewExists && !manifest) {
    return null;
  }

  const workspace = reviewExists ? await getDealWorkspace(dealId, user) : null;

  return {
    dealId,
    companyName: workspace?.companyName ?? inferCompanyNameFromDocuments(documents) ?? "",
    documentCount: documents.length || manifest.document_count || 0,
    fieldCount: Object.keys(workspace?.review?.fields ?? {}).length,
    workbookReady: Boolean(workbookPath || workbookExistsInCloud),
    workbookFileName: workbookPath ? path.basename(workbookPath) : `${dealId}_valuation_model.xlsx`,
    workbookSummary,
    hasReview: Boolean(workspace),
    extractionMetadata,
    runHistory,
    meta,
    documents,
    pipeline: workspace?.pipeline ?? buildPipelineFromPresence({
      hasDocuments: documents.length > 0,
      hasReview: Boolean(workspace),
      workbookReady: Boolean(workbookPath || workbookExistsInCloud),
      extractionMetadata,
    })
  };
}

export async function getDealWorkspace(dealId, user = null) {
  const reviewPath = path.join(RESOLVED_ROOT, `${dealId}_review_payload.json`);
  const manifestPath = path.join(NORMALIZED_ROOT, `${dealId}_manifest.json`);
  const workbookPath = await getWorkbookPath(dealId);
  const workbookExistsInCloud = await hasSupabaseArtifact(dealId, `${dealId}_valuation_model.xlsx`);
  const overrides = await getDealOverrides(dealId, user);
  const extractionMetadata = await getExtractionMetadata(dealId);
  const review = (await exists(reviewPath))
    ? JSON.parse(await fs.readFile(reviewPath, "utf-8"))
    : await getSupabaseArtifactJson(dealId, `${dealId}_review_payload.json`);
  const manifest = (await exists(manifestPath))
    ? JSON.parse(await fs.readFile(manifestPath, "utf-8"))
    : (await getSupabaseArtifactJson(dealId, `${dealId}_manifest.json`)) ?? { document_count: 0, documents: [] };

  if (!review) {
    return null;
  }

  const mergedReview = applyOverridesToReview(review, overrides);

  return {
    dealId,
    companyName: mergedReview.fields?.company_name?.selected?.value ?? "Unknown company",
    documentCount: manifest.document_count ?? manifest.documents?.length ?? 0,
    workbookReady: Boolean(workbookPath || workbookExistsInCloud),
    review: mergedReview,
    overrides,
    extractionMetadata,
    pipeline: buildPipelineFromReview(mergedReview, manifest, Boolean(workbookPath || workbookExistsInCloud), extractionMetadata)
  };
}

export async function createDealFromUploads(dealName, files, user = null) {
  const dealId = slugifyDealName(dealName);
  const dealDir = path.join(INBOX_ROOT, dealId);
  await fs.mkdir(dealDir, { recursive: true });

  const uploadedDocuments = [];

  for (const file of files.slice(0, 5)) {
    const sanitizedName = sanitizeFileName(file.name);
    const filePath = path.join(dealDir, sanitizedName);
    const buffer = Buffer.from(await file.arrayBuffer());
    const sha256 = crypto.createHash("sha256").update(buffer).digest("hex");
    await fs.writeFile(filePath, buffer);
    uploadedDocuments.push({
      fileName: sanitizedName,
      mimeType: file.type || getContentType(sanitizedName),
      sizeBytes: buffer.byteLength,
      sha256,
      buffer,
    });
  }

  await saveDealMeta(dealId, {
    deal_id: dealId,
    display_name: dealName.trim(),
    is_example: false,
    visibility: "private",
    source: "upload",
  });

  await syncDealToSupabase({
    dealId,
    displayName: dealName.trim(),
    userId: user?.id ?? null,
    documents: uploadedDocuments,
    source: "upload",
  });

  return getDealDetail(dealId);
}

export async function createDealFromManualInputs(dealName, inputs, user = null) {
  const dealId = slugifyDealName(dealName);

  await saveDealMeta(dealId, {
    deal_id: dealId,
    display_name: dealName.trim(),
    is_example: false,
    visibility: "private",
    source: "manual_entry",
  });

  await syncDealToSupabase({
    dealId,
    displayName: dealName.trim(),
    userId: user?.id ?? null,
    documents: [],
    source: "manual_entry",
  });

  await fs.mkdir(NORMALIZED_ROOT, { recursive: true });
  const manifestPath = path.join(NORMALIZED_ROOT, `${dealId}_manifest.json`);
  const candidatePath = path.join(NORMALIZED_ROOT, `${dealId}_field_candidates.json`);
  const normalizedCandidatePath = path.join(NORMALIZED_ROOT, `${dealId}_field_candidates_normalized.json`);
  const extractionMetadataPath = path.join(NORMALIZED_ROOT, `${dealId}_extraction_metadata.json`);

  const candidates = Object.entries(inputs || {})
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([fieldName, value]) => ({
      field_name: fieldName,
      value,
      confidence: 0.95,
      source_document_id: "manual_entry",
      source_locator: "manual_entry",
      method: "manual_entry",
      notes: "Provided directly by the user.",
      source_urls: [],
    }));

  await fs.writeFile(
    manifestPath,
    JSON.stringify(
      {
        deal_id: dealId,
        document_count: 0,
        chunk_count: 0,
        manifest_fingerprint: `manual:${dealId}`,
        chunk_chars: 0,
        chunk_overlap_chars: 0,
        documents: [],
        chunks: [],
      },
      null,
      2
    ),
    "utf-8"
  );

  await fs.writeFile(
    candidatePath,
    JSON.stringify(
      {
        deal_id: dealId,
        model: "manual_entry",
        candidate_count: candidates.length,
        candidates,
      },
      null,
      2
    ),
    "utf-8"
  );

  await fs.writeFile(
    extractionMetadataPath,
    JSON.stringify(
      {
        deal_id: dealId,
        cache_key: `manual:${dealId}`,
        manifest_fingerprint: `manual:${dealId}`,
        selected_chunk_ids: [],
        selected_chunk_count: 0,
        model: "manual_entry",
        prompt_version: "manual_entry",
        schema_version: "manual_entry",
        cached: false,
        cache_hit_count: 0,
        generated_at: new Date().toISOString(),
        normalized_path: candidatePath,
        raw_output_path: null,
        source: "manual_entry",
      },
      null,
      2
    ),
    "utf-8"
  );

  await fs.rm(normalizedCandidatePath, { force: true });
  await runPythonCommand(["run_resolve_fields.py", dealId]);
  await runPythonCommand(["run_prepare_model_inputs.py", dealId]);
  await syncLocalArtifactsToSupabase(dealId, [
    `${dealId}_manifest.json`,
    `${dealId}_extraction_metadata.json`,
    `${dealId}_review_payload.json`,
    `${dealId}_model_input.json`,
    `${dealId}_field_candidates.json`,
    `${dealId}_field_candidates_normalized.json`,
    `${dealId}_resolved.json`,
  ]);

  return getDealDetail(dealId, user);
}

export async function runDealPipeline(dealId, { phase = "extract", maxChunks = 5, userId = null } = {}) {
  if (isRailwayWorkerConfigured()) {
    if (phase === "analysis") {
      const user = userId ? { id: userId } : null;
      if (userId) {
        const overrides = await getDealOverrides(dealId, user);
        await fs.mkdir(OVERRIDES_ROOT, { recursive: true });
        await fs.writeFile(getOverridePath(dealId), JSON.stringify(overrides, null, 2), "utf-8");
      }
      await refreshMaterializedDealArtifacts(dealId, user);
      const modelInputPath = path.join(RESOLVED_ROOT, `${dealId}_model_input.json`);
      const modelInput = JSON.parse(await fs.readFile(modelInputPath, "utf-8"));
      console.log("[runDealPipeline] before remote worker trigger", {
        dealId,
        phase,
        userId,
        modelInputRevenue: modelInput.revenue ?? null,
      });
      await syncLocalArtifactsToSupabase(dealId, [
        `${dealId}_review_payload.json`,
        `${dealId}_model_input.json`,
        `${dealId}_resolved.json`,
      ]);
    }
    return triggerRailwayPipeline(dealId, { phase, maxChunks, userId });
  }

  if (phase === "analysis") {
    const user = userId ? { id: userId } : null;
    if (userId) {
      const overrides = await getDealOverrides(dealId, { id: userId });
      await fs.mkdir(OVERRIDES_ROOT, { recursive: true });
      await fs.writeFile(getOverridePath(dealId), JSON.stringify(overrides, null, 2), "utf-8");
      console.log("[runDealPipeline] synced user overrides", {
        dealId,
        userId,
        overrideRevenue: overrides.revenue ?? null,
      });
    }
    await refreshMaterializedDealArtifacts(dealId, user);
    const modelInputPath = path.join(RESOLVED_ROOT, `${dealId}_model_input.json`);
    const modelInput = JSON.parse(await fs.readFile(modelInputPath, "utf-8"));
    console.log("[runDealPipeline] before workbook build", {
      dealId,
      phase,
      modelInputRevenue: modelInput.revenue ?? null,
      modelInputEntryMultiple: modelInput.entry_multiple ?? null,
    });
    await runPythonCommand(["run_build_workbook_from_deal.py", dealId]);
    const result = { phase, cached: false, message: "Analysis completed." };
    await appendDealRun(dealId, {
      phase,
      status: "completed",
      cached: false,
      message: result.message,
    });
    await appendSupabasePipelineRun(dealId, {
      owner_user_id: null,
      phase,
      status: "completed",
      cached: false,
      message: result.message,
    });
    return result;
  }

  await runPythonCommand(["run_local_ingestion.py", dealId]);
  const extractionResult = await runPythonCommand([
    "run_chunk_extraction.py",
    dealId,
    "--max-chunks",
    String(maxChunks),
  ]);
  await runPythonCommand(["run_resolve_fields.py", dealId]);
  await runPythonCommand(["run_prepare_model_inputs.py", dealId]);
  const cached = extractionResult.stdout.includes("Cache hit: reused prior extraction artifacts");
  const result = {
    phase,
    cached,
    message: cached ? "Using cached extraction artifacts." : "Ran fresh extraction."
  };
  await appendDealRun(dealId, {
    phase,
    status: "completed",
    cached,
    message: result.message,
  });
  await appendSupabasePipelineRun(dealId, {
    owner_user_id: null,
    phase,
    status: "completed",
    cached,
    message: result.message,
  });
  return result;
}

export async function getPipelineRunStatus(jobId) {
  if (!isRailwayWorkerConfigured()) {
    return null;
  }

  const response = await fetch(`${getRailwayWorkerUrl()}/pipeline/run/${jobId}`, {
    method: "GET",
    headers: buildWorkerHeaders(),
    cache: "no-store",
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || "Failed to fetch worker job status.");
  }

  return payload;
}

export async function getDealOverrides(dealId, user = null) {
  if (user?.id) {
    const cloudOverrides = await getSupabaseOverrides(dealId, user.id);
    if (cloudOverrides) {
      return cloudOverrides;
    }
  }

  return getLocalOverrides(dealId);
}

export async function saveDealOverride(dealId, fieldName, value, user = null) {
  const overrides = await getDealOverrides(dealId, user);
  overrides[fieldName] = value;
  if (fieldName === "revenue") {
    console.log("[saveDealOverride] incoming revenue override", {
      dealId,
      userId: user?.id ?? null,
      value,
    });
  }
  await writeOverrides(dealId, overrides, user);
  await refreshMaterializedDealArtifacts(dealId, user);
  return getDealWorkspace(dealId, user);
}

export async function clearDealOverride(dealId, fieldName, user = null) {
  const overrides = await getDealOverrides(dealId, user);
  delete overrides[fieldName];
  await writeOverrides(dealId, overrides, user);
  await refreshMaterializedDealArtifacts(dealId, user);
  return getDealWorkspace(dealId, user);
}

export async function applyRecommendedEstimates(dealId, user = null) {
  const workspace = await getDealWorkspace(dealId, user);
  if (!workspace) {
    throw new Error("Deal workspace not found.");
  }

  const overrides = await getDealOverrides(dealId, user);
  let appliedCount = 0;

  for (const [fieldName, fieldState] of Object.entries(workspace.review.fields ?? {})) {
    const estimate = fieldState?.recommended_estimate;
    if (!estimate) {
      continue;
    }
    if (fieldState?.selected?.method === "user_override") {
      continue;
    }

    overrides[fieldName] = estimate.normalized_value ?? estimate.value;
    appliedCount += 1;
  }

  if (appliedCount === 0) {
    return { workspace, appliedCount: 0 };
  }

  await writeOverrides(dealId, overrides, user);
  await refreshMaterializedDealArtifacts(dealId, user);
  return {
    workspace: await getDealWorkspace(dealId, user),
    appliedCount,
  };
}

async function writeOverrides(dealId, overrides, user = null) {
  await fs.mkdir(OVERRIDES_ROOT, { recursive: true });
  const overridePath = getOverridePath(dealId);
  await fs.writeFile(overridePath, JSON.stringify(overrides, null, 2), "utf-8");

  if (user?.id) {
    await writeSupabaseOverrides(dealId, overrides, user.id);
  }
}

async function refreshMaterializedDealArtifacts(dealId, user = null) {
  const workspace = await getDealWorkspace(dealId, user);
  if (!workspace?.review?.fields) {
    return;
  }

  const revisionId = new Date().toISOString();
  const materializedReview = {
    ...workspace.review,
    artifact_revision_id: revisionId,
    artifact_revision_reason: "override_update",
  };
  const materializedResolved = buildResolvedFromReview(materializedReview, dealId, revisionId);
  const materializedModelInput = buildModelInputFromReview(materializedReview);

  await fs.mkdir(RESOLVED_ROOT, { recursive: true });
  await fs.writeFile(
    path.join(RESOLVED_ROOT, `${dealId}_review_payload.json`),
    JSON.stringify(materializedReview, null, 2),
    "utf-8"
  );
  await fs.writeFile(
    path.join(RESOLVED_ROOT, `${dealId}_resolved.json`),
    JSON.stringify(materializedResolved, null, 2),
    "utf-8"
  );
  await fs.writeFile(
    path.join(RESOLVED_ROOT, `${dealId}_model_input.json`),
    JSON.stringify(materializedModelInput, null, 2),
    "utf-8"
  );

  console.log("[refreshMaterializedDealArtifacts] wrote materialized artifacts", {
    dealId,
    userId: user?.id ?? null,
    selectedRevenue: materializedReview?.fields?.revenue?.selected?.value ?? null,
    selectedRevenueMethod: materializedReview?.fields?.revenue?.selected?.method ?? null,
    modelInputRevenue: materializedModelInput?.revenue ?? null,
    overrideRevenue: workspace?.overrides?.revenue ?? null,
    revisionId,
  });

  await writeMaterializedVersionSnapshot(dealId, revisionId, {
    review: materializedReview,
    resolved: materializedResolved,
    model_input: materializedModelInput,
  });

  await invalidateWorkbookArtifacts(dealId);
  await syncLocalArtifactsToSupabase(dealId, [
    `${dealId}_review_payload.json`,
    `${dealId}_model_input.json`,
    `${dealId}_resolved.json`,
  ]);
}

export async function getDealDocuments(dealId) {
  const sources = [
    { root: INBOX_ROOT, bucket: "inbox" },
    { root: PROCESSED_ROOT, bucket: "processed" }
  ];

  const documents = [];
  const seen = new Set();

  for (const source of sources) {
    const dirPath = path.join(source.root, dealId);
    for (const fileName of await safeReadDir(dirPath)) {
      const filePath = path.join(dirPath, fileName);
      const stat = await safeStat(filePath);
      if (!stat?.isFile()) {
        continue;
      }

      const key = fileName.toLowerCase();
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);

      documents.push({
        fileName,
        filePath,
        size: stat.size,
        bucket: source.bucket
      });
    }
  }

  const supabaseDocuments = await getSupabaseDocuments(dealId);
  for (const document of supabaseDocuments) {
    const key = `${document.fileName.toLowerCase()}::cloud`;
    if (seen.has(document.fileName.toLowerCase())) {
      continue;
    }
    seen.add(key);
    documents.push(document);
  }

  return documents.sort((a, b) => a.fileName.localeCompare(b.fileName));
}

export async function getDealDocumentResponse(dealId, requestedFileName) {
  const documents = await getDealDocuments(dealId);
  const document = documents.find((item) => item.fileName === requestedFileName);
  if (!document) {
    return null;
  }

  if (!document.filePath && document.storagePath) {
    return getSupabaseDocumentResponse(document);
  }

  const body = await fs.readFile(document.filePath);
  return {
    body,
    headers: {
      "Content-Type": getContentType(document.fileName),
      "Content-Disposition": `inline; filename="${document.fileName}"`
    }
  };
}

export async function getDealWorkbookResponse(dealId) {
  if (isRailwayWorkerConfigured()) {
    const remoteResponse = await getSupabaseWorkbookResponse(dealId);
    if (remoteResponse) {
      return remoteResponse;
    }
  }

  const workbookPath = await getWorkbookPath(dealId);
  if (workbookPath) {
    const body = await fs.readFile(workbookPath);
    return {
      body,
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="${path.basename(workbookPath)}"`
      }
    };
  }

  return getSupabaseWorkbookResponse(dealId);
}

export async function getExtractionMetadata(dealId) {
  const metadataPath = path.join(NORMALIZED_ROOT, `${dealId}_extraction_metadata.json`);
  if (!(await exists(metadataPath))) {
    return getSupabaseArtifactJson(dealId, `${dealId}_extraction_metadata.json`);
  }

  return JSON.parse(await fs.readFile(metadataPath, "utf-8"));
}

export async function getDealRunHistory(dealId) {
  const runPath = getRunHistoryPath(dealId);
  if (!(await exists(runPath))) {
    return { deal_id: dealId, runs: [] };
  }

  return JSON.parse(await fs.readFile(runPath, "utf-8"));
}

export async function getDealMeta(dealId) {
  const metaPath = getDealMetaPath(dealId);
  if (!(await exists(metaPath))) {
    return {
      deal_id: dealId,
      display_name: null,
      is_example: false,
      visibility: "private",
      source: "discovered",
    };
  }

  return JSON.parse(await fs.readFile(metaPath, "utf-8"));
}

export async function getWorkbookSummary(dealId) {
  if (isRailwayWorkerConfigured()) {
    const remoteSummary = await getSupabaseArtifactJson(dealId, `${dealId}_summary.json`);
    if (remoteSummary) {
      return remoteSummary;
    }
  }

  const summaryPath = path.join(OUTPUTS_ROOT, `${dealId}_summary.json`);
  if (!(await exists(summaryPath))) {
    return getSupabaseArtifactJson(dealId, `${dealId}_summary.json`);
  }

  return JSON.parse(await fs.readFile(summaryPath, "utf-8"));
}

function getOverridePath(dealId) {
  return path.join(OVERRIDES_ROOT, `${dealId}_overrides.json`);
}

function getDealMetaPath(dealId) {
  return path.join(DEAL_METADATA_ROOT, `${dealId}.json`);
}

function getRunHistoryPath(dealId) {
  return path.join(PIPELINE_RUNS_ROOT, `${dealId}_runs.json`);
}

async function getAllDealIds() {
  const ids = new Set();

  for (const sourceRoot of [INBOX_ROOT, PROCESSED_ROOT]) {
    for (const name of await safeReadDir(sourceRoot)) {
      if (!name.startsWith(".")) {
        ids.add(name);
      }
    }
  }

  for (const fileName of await safeReadDir(RESOLVED_ROOT)) {
    if (fileName.endsWith("_review_payload.json")) {
      ids.add(fileName.replace("_review_payload.json", ""));
    }
  }

  return Array.from(ids).sort();
}

async function getCuratedExampleDealIds() {
  const ids = new Set();

  for (const fileName of await safeReadDir(DEAL_METADATA_ROOT)) {
    if (!fileName.endsWith(".json")) {
      continue;
    }
    const payload = JSON.parse(
      await fs.readFile(path.join(DEAL_METADATA_ROOT, fileName), "utf-8")
    );
    if (payload?.is_example === true || payload?.visibility === "public_example") {
      ids.add(String(payload.deal_id || fileName.replace(/\.json$/, "")));
    }
  }

  for (const dealId of getStaticCuratedExampleDealIds()) {
    ids.add(dealId);
  }

  return Array.from(ids);
}

async function saveDealMeta(dealId, payload) {
  await fs.mkdir(DEAL_METADATA_ROOT, { recursive: true });
  await fs.writeFile(getDealMetaPath(dealId), JSON.stringify(payload, null, 2), "utf-8");
}

async function appendDealRun(dealId, run) {
  const existing = await getDealRunHistory(dealId);
  existing.deal_id = dealId;
  existing.runs = existing.runs || [];
  existing.runs.unshift({
    run_at: new Date().toISOString(),
    ...run,
  });
  existing.runs = existing.runs.slice(0, 25);

  await fs.mkdir(PIPELINE_RUNS_ROOT, { recursive: true });
  await fs.writeFile(getRunHistoryPath(dealId), JSON.stringify(existing, null, 2), "utf-8");
}

async function syncDealToSupabase({ dealId, displayName, userId, documents, source = "upload" }) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return;
  }

  const bucket = getSupabaseStorageBucket();
  await withSupabaseRetries(
    () =>
      upsertSupabaseDeal(supabase, {
        deal_id: dealId,
        owner_user_id: userId,
        display_name: displayName,
        visibility: "private",
        is_example: false,
        source,
      }),
    `save deal metadata for ${dealId}`
  );

  for (const document of documents) {
    const storagePath = buildSupabaseStoragePath({
      userId,
      dealId,
      fileName: document.fileName,
    });

    await withSupabaseRetries(
      () =>
        uploadToSupabaseOrThrow(
          supabase,
          bucket,
          storagePath,
          document.buffer,
          document.mimeType
        ),
      `upload ${document.fileName} to Supabase Storage`
    );

    const { error: documentError } = await withSupabaseRetries(
      () =>
        supabase.from("documents").upsert(
          {
            deal_id: dealId,
            owner_user_id: userId,
            file_name: document.fileName,
            mime_type: document.mimeType,
            size_bytes: document.sizeBytes,
            sha256: document.sha256,
            storage_bucket: bucket,
            storage_path: storagePath,
            source: "upload",
          },
          {
            onConflict: "deal_id,storage_bucket,storage_path",
          }
        ),
      `save document metadata for ${document.fileName}`
    );

    if (documentError) {
      throw new Error(`Failed to save document metadata: ${documentError.message}`);
    }
  }
}

async function syncLocalArtifactsToSupabase(dealId, fileNames) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return;
  }

  const bucket = getSupabaseStorageBucket();
  for (const fileName of fileNames) {
    const localPath = resolveArtifactLocalPath(fileName);
    if (!localPath || !(await exists(localPath))) {
      continue;
    }
    const body = await fs.readFile(localPath);
    const storagePath = buildSupabaseArtifactPath(dealId, fileName);
    const contentType = fileName.endsWith(".json") ? "application/json" : "application/octet-stream";
    await withSupabaseRetries(
      () =>
        uploadToSupabaseOrThrow(
          supabase,
          bucket,
          storagePath,
          body,
          contentType
        ),
      `upload artifact ${fileName} to Supabase Storage`
    );
  }
}

async function upsertSupabaseDeal(supabase, payload) {
  const { error } = await supabase.from("deals").upsert(payload, {
    onConflict: "deal_id",
  });

  if (error) {
    throw new Error(`Failed to save deal metadata: ${error.message}`);
  }
}

async function appendSupabasePipelineRun(dealId, payload) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return;
  }

  const { error } = await withSupabaseRetries(
    () =>
      supabase.from("pipeline_runs").insert({
        deal_id: dealId,
        ...payload,
        triggered_by: "frontend",
      }),
    `save pipeline run metadata for ${dealId}`
  );

  if (error) {
    throw new Error(`Failed to save pipeline run metadata: ${error.message}`);
  }
}

async function triggerRailwayPipeline(dealId, { phase, maxChunks, userId = null }) {
  const response = await fetch(`${getRailwayWorkerUrl()}/pipeline/run`, {
    method: "POST",
    headers: {
      ...buildWorkerHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      deal_id: dealId,
      phase,
      max_chunks: maxChunks,
      triggered_by: "frontend",
      user_id: userId,
    }),
    cache: "no-store",
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || "Failed to start Railway worker job.");
  }

  return {
    phase,
    remote: true,
    jobId: payload.job_id,
    status: payload.status || "queued",
    message: "Pipeline job queued on Railway worker.",
  };
}

function buildWorkerHeaders() {
  const sharedSecret = getWorkerSharedSecret();
  return sharedSecret ? { Authorization: `Bearer ${sharedSecret}` } : {};
}

function isRailwayWorkerConfigured() {
  return Boolean(getRailwayWorkerUrl());
}

async function withSupabaseRetries(fn, actionLabel, attempts = 3) {
  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt >= attempts || !isRetryableSupabaseError(error)) {
        break;
      }
      const delayMs = attempt * 600;
      console.warn(`Retrying Supabase operation: ${actionLabel} (attempt ${attempt + 1}/${attempts})`);
      await sleep(delayMs);
    }
  }

  throw lastError;
}

function isRetryableSupabaseError(error) {
  const message = String(error?.message || error || "").toLowerCase();
  return (
    message.includes("timed out") ||
    message.includes("timeout") ||
    message.includes("bad gateway") ||
    message.includes("502") ||
    message.includes("connection") ||
    message.includes("network") ||
    message.includes("fetch failed") ||
    message.includes("socket") ||
    message.includes("econnreset") ||
    message.includes("service unavailable")
  );
}

async function uploadToSupabaseOrThrow(supabase, bucket, storagePath, body, contentType) {
  const result = await supabase.storage.from(bucket).upload(storagePath, body, {
    contentType,
    upsert: true,
  });

  if (result?.error) {
    throw new Error(result.error.message || `Failed upload to ${storagePath}`);
  }

  return result;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getSupabaseDocuments(dealId) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return [];
  }

  const { data, error } = await supabase
    .from("documents")
    .select("file_name, mime_type, size_bytes, storage_bucket, storage_path")
    .eq("deal_id", dealId);

  if (error) {
    throw new Error(`Failed to load Supabase documents: ${error.message}`);
  }

  return (data ?? []).map((row) => ({
    fileName: row.file_name,
    filePath: null,
    size: row.size_bytes,
    bucket: "supabase",
    storageBucket: row.storage_bucket,
    storagePath: row.storage_path,
    mimeType: row.mime_type,
  }));
}

async function getSupabaseDocumentResponse(document) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return null;
  }

  const bucket = document.storageBucket || getSupabaseStorageBucket();
  const { data, error } = await supabase.storage.from(bucket).download(document.storagePath);
  if (error || !data) {
    throw new Error(`Failed to download Supabase document: ${error?.message || "Unknown error"}`);
  }

  const arrayBuffer = await data.arrayBuffer();
  return {
    body: Buffer.from(arrayBuffer),
    headers: {
      "Content-Type": document.mimeType || getContentType(document.fileName),
      "Content-Disposition": `inline; filename="${document.fileName}"`,
    },
  };
}

async function getSupabaseArtifactJson(dealId, fileName) {
  const response = await getSupabaseArtifactResponse(dealId, fileName);
  if (!response) {
    return null;
  }

  try {
    return JSON.parse(response.body.toString("utf-8"));
  } catch {
    return null;
  }
}

async function getSupabaseWorkbookResponse(dealId) {
  return getSupabaseArtifactResponse(dealId, `${dealId}_valuation_model.xlsx`, {
    contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    disposition: `attachment; filename="${dealId}_valuation_model.xlsx"`,
  });
}

async function getSupabaseArtifactResponse(dealId, fileName, options = {}) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return null;
  }

  const bucket = getSupabaseStorageBucket();
  const storagePath = buildSupabaseArtifactPath(dealId, fileName);
  const { data, error } = await supabase.storage.from(bucket).download(storagePath);
  if (error || !data) {
    return null;
  }

  const arrayBuffer = await data.arrayBuffer();
  return {
    body: Buffer.from(arrayBuffer),
    headers: {
      "Content-Type": options.contentType || "application/json",
      "Content-Disposition": options.disposition || `inline; filename="${fileName}"`,
    },
  };
}

async function hasSupabaseArtifact(dealId, fileName) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return false;
  }

  const bucket = getSupabaseStorageBucket();
  const storagePath = buildSupabaseArtifactPath(dealId, fileName);
  const { data, error } = await supabase.storage.from(bucket).download(storagePath);
  return Boolean(!error && data);
}

async function deleteSupabaseArtifacts(dealId, fileNames) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase || fileNames.length === 0) {
    return;
  }

  const bucket = getSupabaseStorageBucket();
  const storagePaths = fileNames.map((fileName) => buildSupabaseArtifactPath(dealId, fileName));
  const { error } = await supabase.storage.from(bucket).remove(storagePaths);
  if (error) {
    throw new Error(`Failed to clear stale Supabase artifacts: ${error.message}`);
  }
}

function buildSupabaseStoragePath({ userId, dealId, fileName }) {
  const owner = userId || "anonymous";
  return `private/${owner}/${dealId}/${fileName}`;
}

function buildSupabaseArtifactPath(dealId, fileName) {
  return `artifacts/${dealId}/${fileName}`;
}

function resolveArtifactLocalPath(fileName) {
  if (fileName.endsWith("_review_payload.json") || fileName.endsWith("_model_input.json") || fileName.endsWith("_resolved.json")) {
    return path.join(RESOLVED_ROOT, fileName);
  }
  if (
    fileName.endsWith("_manifest.json") ||
    fileName.endsWith("_field_candidates.json") ||
    fileName.endsWith("_field_candidates_normalized.json")
  ) {
    return path.join(NORMALIZED_ROOT, fileName);
  }
  if (fileName.endsWith(".xlsx") || fileName.endsWith("_summary.json") || fileName.endsWith("_diagnostics.json")) {
    return path.join(OUTPUTS_ROOT, fileName);
  }
  return null;
}

function applyOverridesToReview(review, overrides) {
  if (!review?.fields || !overrides || Object.keys(overrides).length === 0) {
    return review;
  }

  const fields = {};
  for (const [fieldName, fieldState] of Object.entries(review.fields)) {
    if (!(fieldName in overrides)) {
      fields[fieldName] = fieldState;
      continue;
    }

    fields[fieldName] = {
      ...fieldState,
      selected: {
        value: overrides[fieldName],
        confidence: 1,
        source_document_id: null,
        source_locator: "user_override",
        method: "user_override",
        notes: "Applied from saved override.",
        source_urls: [],
      },
    };
  }

  return {
    ...review,
    fields,
  };
}

function buildModelInputFromReview(review) {
  const modelInput = {};

  for (const [fieldName, fieldState] of Object.entries(review?.fields ?? {})) {
    modelInput[fieldName] = fieldState?.selected?.value ?? null;
  }

  return modelInput;
}

function buildResolvedFromReview(review, dealId, revisionId) {
  const resolvedFields = {};

  for (const [fieldName, fieldState] of Object.entries(review?.fields ?? {})) {
    resolvedFields[fieldName] = {
      ...(fieldState?.selected ?? {}),
    };
  }

  return {
    deal_id: dealId,
    artifact_revision_id: revisionId,
    resolved_fields: resolvedFields,
  };
}

async function writeMaterializedVersionSnapshot(dealId, revisionId, payload) {
  const safeRevisionId = revisionId.replace(/[:.]/g, "-");
  const versionRoot = path.join(PIPELINE_STATE_ROOT, "deal_versions", dealId);
  await fs.mkdir(versionRoot, { recursive: true });
  await fs.writeFile(
    path.join(versionRoot, `${safeRevisionId}.json`),
    JSON.stringify(
      {
        deal_id: dealId,
        revision_id: revisionId,
        created_at: revisionId,
        payload,
      },
      null,
      2
    ),
    "utf-8"
  );
}

async function invalidateWorkbookArtifacts(dealId) {
  const localArtifacts = [
    path.join(OUTPUTS_ROOT, `${dealId}_valuation_model.xlsx`),
    path.join(OUTPUTS_ROOT, `${dealId}_summary.json`),
    path.join(OUTPUTS_ROOT, `${dealId}_diagnostics.json`),
  ];

  await Promise.all(localArtifacts.map((filePath) => fs.rm(filePath, { force: true })));
  await deleteSupabaseArtifacts(dealId, [
    `${dealId}_valuation_model.xlsx`,
    `${dealId}_summary.json`,
    `${dealId}_diagnostics.json`,
  ]);
}

async function getWorkbookPath(dealId) {
  if (isRailwayWorkerConfigured()) {
    const remoteExists = await hasSupabaseArtifact(dealId, `${dealId}_valuation_model.xlsx`);
    if (remoteExists) {
      return null;
    }
  }
  const candidate = path.join(OUTPUTS_ROOT, `${dealId}_valuation_model.xlsx`);
  return (await exists(candidate)) ? candidate : null;
}

async function getLocalOverrides(dealId) {
  const overridePath = getOverridePath(dealId);
  if (!(await exists(overridePath))) {
    return {};
  }
  const payload = JSON.parse(await fs.readFile(overridePath, "utf-8"));
  return typeof payload === "object" && payload ? payload : {};
}

async function getSupabaseOverrides(dealId, userId) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    return null;
  }

  const { data, error } = await supabase
    .from("user_overrides")
    .select("field_name, override_value")
    .eq("deal_id", dealId)
    .eq("user_id", userId);

  if (error) {
    throw new Error(`Failed to load Supabase overrides: ${error.message}`);
  }

  const overrides = {};
  for (const row of data ?? []) {
    overrides[row.field_name] = row.override_value;
  }

  return overrides;
}

async function writeSupabaseOverrides(dealId, overrides, userId) {
  const supabase = getSupabaseServiceRoleClient();
  if (!supabase) {
    throw new Error("Supabase service role client is not configured.");
  }

  const nextRows = Object.entries(overrides).map(([fieldName, overrideValue]) => ({
    user_id: userId,
    deal_id: dealId,
    field_name: fieldName,
    override_value: overrideValue
  }));

  const { data: existingRows, error: existingError } = await supabase
    .from("user_overrides")
    .select("field_name")
    .eq("deal_id", dealId)
    .eq("user_id", userId);

  if (existingError) {
    throw new Error(`Failed to load existing Supabase overrides: ${existingError.message}`);
  }

  const nextFieldNames = new Set(nextRows.map((row) => row.field_name));
  const staleFieldNames = (existingRows ?? [])
    .map((row) => row.field_name)
    .filter((fieldName) => !nextFieldNames.has(fieldName));

  if (staleFieldNames.length > 0) {
    const { error: deleteError } = await supabase
      .from("user_overrides")
      .delete()
      .eq("deal_id", dealId)
      .eq("user_id", userId)
      .in("field_name", staleFieldNames);

    if (deleteError) {
      throw new Error(`Failed to clear Supabase overrides: ${deleteError.message}`);
    }
  }

  if (nextRows.length === 0) {
    return;
  }

  const { error: upsertError } = await supabase.from("user_overrides").upsert(nextRows, {
    onConflict: "user_id,deal_id,field_name",
  });
  if (upsertError) {
    throw new Error(`Failed to save Supabase overrides: ${upsertError.message}`);
  }
}

async function runPythonCommand(args) {
  try {
    return await execFileAsync("python3", args, { cwd: REPO_ROOT });
  } catch (error) {
    const stderr = typeof error?.stderr === "string" ? error.stderr.trim() : "";
    const stdout = typeof error?.stdout === "string" ? error.stdout.trim() : "";
    const detail = stderr || stdout || error.message || "Unknown Python execution error.";
    throw new Error(detail);
  }
}

function hasExtractedCandidates(review) {
  return Object.values(review.fields ?? {}).some((fieldState) =>
    (fieldState.options ?? []).some((option) => option.method === "extracted")
  );
}

function hasNormalizedCandidates(review) {
  return Object.values(review.fields ?? {}).some((fieldState) =>
    (fieldState.options ?? []).some((option) => option.normalized_value !== undefined)
  );
}

function buildPipelineFromReview(review, manifest, workbookReady, extractionMetadata) {
  return [
    {
      name: "Reading inputs",
      status: manifest.documents?.length ? "Complete" : "Pending",
    },
    {
      name: "Extracting",
      status: hasExtractedCandidates(review) ? "Complete" : "Pending",
      detail: extractionMetadata?.cached ? "Using cached extraction" : "Fresh extraction",
    },
    { name: "Normalizing", status: hasNormalizedCandidates(review) ? "Complete" : "Pending" },
    { name: "Overrides", status: "Ready" },
    { name: "Workbook", status: workbookReady ? "Built" : "Pending" },
  ];
}

function buildPipelineFromPresence({ hasDocuments, hasReview, workbookReady, extractionMetadata }) {
  return [
    { name: "Reading inputs", status: hasDocuments ? "Complete" : "Pending" },
    {
      name: "Extracting",
      status: hasReview ? "Complete" : "Pending",
      detail: extractionMetadata?.cached ? "Using cached extraction" : "Not cached yet",
    },
    { name: "Normalizing", status: hasReview ? "Complete" : "Pending" },
    { name: "Overrides", status: hasReview ? "Ready" : "Pending" },
    { name: "Workbook", status: workbookReady ? "Built" : "Pending" }
  ];
}

function slugifyDealName(input) {
  return String(input)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48) || "deal";
}

function sanitizeFileName(fileName) {
  return path.basename(fileName).replace(/[^\w.\- ()]/g, "_");
}

function inferCompanyNameFromDocuments(documents) {
  if (!documents.length) {
    return "";
  }

  return documents[0].fileName.replace(/\.[^.]+$/, "");
}

function getContentType(fileName) {
  const extension = path.extname(fileName).toLowerCase();
  if (extension === ".pdf") {
    return "application/pdf";
  }
  if (extension === ".txt") {
    return "text/plain; charset=utf-8";
  }
  if (extension === ".html" || extension === ".htm") {
    return "text/html; charset=utf-8";
  }
  if (extension === ".md") {
    return "text/markdown; charset=utf-8";
  }
  return "application/octet-stream";
}

async function safeReadDir(dirPath) {
  try {
    return await fs.readdir(dirPath);
  } catch {
    return [];
  }
}

async function safeStat(filePath) {
  try {
    return await fs.stat(filePath);
  } catch {
    return null;
  }
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
