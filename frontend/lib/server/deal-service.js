import { promises as fs } from "fs";
import path from "path";
import { execFile } from "child_process";
import crypto from "crypto";
import { promisify } from "util";

import { getSupabaseServiceRoleClient } from "@/lib/supabase/service-role";
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
  const deals = await getAvailableDeals();
  return deals.filter((deal) => deal.meta?.is_example !== false);
}

export async function getDealDetail(dealId, user = null) {
  const reviewPath = path.join(RESOLVED_ROOT, `${dealId}_review_payload.json`);
  const manifestPath = path.join(NORMALIZED_ROOT, `${dealId}_manifest.json`);
  const extractionMetadata = await getExtractionMetadata(dealId);
  const runHistory = await getDealRunHistory(dealId);
  const meta = await getDealMeta(dealId);
  const workbookPath = await getWorkbookPath(dealId);
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
    workbookReady: Boolean(workbookPath),
    workbookFileName: workbookPath ? path.basename(workbookPath) : null,
    workbookSummary,
    hasReview: Boolean(workspace),
    extractionMetadata,
    runHistory,
    meta,
    documents,
    pipeline: workspace?.pipeline ?? buildPipelineFromPresence({
      hasDocuments: documents.length > 0,
      hasReview: Boolean(workspace),
      workbookReady: Boolean(workbookPath),
      extractionMetadata,
    })
  };
}

export async function getDealWorkspace(dealId, user = null) {
  const reviewPath = path.join(RESOLVED_ROOT, `${dealId}_review_payload.json`);
  const manifestPath = path.join(NORMALIZED_ROOT, `${dealId}_manifest.json`);
  const workbookPath = await getWorkbookPath(dealId);
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

  return {
    dealId,
    companyName: review.fields?.company_name?.selected?.value ?? "Unknown company",
    documentCount: manifest.document_count ?? manifest.documents?.length ?? 0,
    workbookReady: Boolean(workbookPath),
    review,
    overrides,
    extractionMetadata,
    pipeline: buildPipelineFromReview(review, manifest, Boolean(workbookPath), extractionMetadata)
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
  });

  return getDealDetail(dealId);
}

export async function runDealPipeline(dealId, { phase = "extract", maxChunks = 5, userId = null } = {}) {
  if (isRailwayWorkerConfigured()) {
    return triggerRailwayPipeline(dealId, { phase, maxChunks, userId });
  }

  if (phase === "analysis") {
    await runPythonCommand(["run_resolve_fields.py", dealId]);
    await runPythonCommand(["run_prepare_model_inputs.py", dealId]);
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
  await writeOverrides(dealId, overrides, user);
  await rerunResolutionArtifacts(dealId);
  return getDealWorkspace(dealId, user);
}

export async function clearDealOverride(dealId, fieldName, user = null) {
  const overrides = await getDealOverrides(dealId, user);
  delete overrides[fieldName];
  await writeOverrides(dealId, overrides, user);
  await rerunResolutionArtifacts(dealId);
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
  await rerunResolutionArtifacts(dealId);
  return {
    workspace: await getDealWorkspace(dealId, user),
    appliedCount,
  };
}

async function writeOverrides(dealId, overrides, user = null) {
  if (user?.id) {
    await writeSupabaseOverrides(dealId, overrides, user.id);
    return;
  }

  await fs.mkdir(OVERRIDES_ROOT, { recursive: true });
  const overridePath = getOverridePath(dealId);
  await fs.writeFile(overridePath, JSON.stringify(overrides, null, 2), "utf-8");
}

async function rerunResolutionArtifacts(dealId) {
  await runPythonCommand(["run_resolve_fields.py", dealId]);
  await runPythonCommand(["run_prepare_model_inputs.py", dealId]);
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
      is_example: true,
      visibility: "example",
      source: "seeded",
    };
  }

  return JSON.parse(await fs.readFile(metaPath, "utf-8"));
}

export async function getWorkbookSummary(dealId) {
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

async function syncDealToSupabase({ dealId, displayName, userId, documents }) {
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
        source: "upload",
      }),
    `save deal metadata for ${dealId}`
  );

  for (const document of documents) {
    const storagePath = buildSupabaseStoragePath({
      userId,
      dealId,
      fileName: document.fileName,
    });

    const { error: uploadError } = await withSupabaseRetries(
      () =>
        supabase.storage.from(bucket).upload(storagePath, document.buffer, {
          contentType: document.mimeType,
          upsert: true,
        }),
      `upload ${document.fileName} to Supabase Storage`
    );

    if (uploadError) {
      throw new Error(`Failed to upload ${document.fileName} to Supabase Storage: ${uploadError.message}`);
    }

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
    message.includes("connection") ||
    message.includes("network") ||
    message.includes("fetch failed") ||
    message.includes("socket") ||
    message.includes("econnreset") ||
    message.includes("service unavailable")
  );
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

function buildSupabaseStoragePath({ userId, dealId, fileName }) {
  const owner = userId || "anonymous";
  return `private/${owner}/${dealId}/${fileName}`;
}

function buildSupabaseArtifactPath(dealId, fileName) {
  return `artifacts/${dealId}/${fileName}`;
}

async function getWorkbookPath(dealId) {
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

  const { error: deleteError } = await supabase
    .from("user_overrides")
    .delete()
    .eq("deal_id", dealId)
    .eq("user_id", userId);

  if (deleteError) {
    throw new Error(`Failed to clear Supabase overrides: ${deleteError.message}`);
  }

  const rows = Object.entries(overrides).map(([fieldName, overrideValue]) => ({
    user_id: userId,
    deal_id: dealId,
    field_name: fieldName,
    override_value: overrideValue
  }));

  if (rows.length === 0) {
    return;
  }

  const { error: insertError } = await supabase.from("user_overrides").insert(rows);
  if (insertError) {
    throw new Error(`Failed to save Supabase overrides: ${insertError.message}`);
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
