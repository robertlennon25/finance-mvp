import { promises as fs } from "fs";
import path from "path";
import { execFile } from "child_process";
import { promisify } from "util";

import { getSupabaseServiceRoleClient } from "@/lib/supabase/service-role";

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

  if (!documents.length && !(await exists(reviewPath)) && !(await exists(manifestPath))) {
    return null;
  }

  const manifest = (await exists(manifestPath))
    ? JSON.parse(await fs.readFile(manifestPath, "utf-8"))
    : { document_count: documents.length, documents: [] };
  const workspace = (await exists(reviewPath)) ? await getDealWorkspace(dealId, user) : null;

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

  if (!(await exists(reviewPath))) {
    return null;
  }

  const review = JSON.parse(await fs.readFile(reviewPath, "utf-8"));
  const manifest = (await exists(manifestPath))
    ? JSON.parse(await fs.readFile(manifestPath, "utf-8"))
    : { document_count: 0, documents: [] };

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

export async function createDealFromUploads(dealName, files) {
  const dealId = slugifyDealName(dealName);
  const dealDir = path.join(INBOX_ROOT, dealId);
  await fs.mkdir(dealDir, { recursive: true });

  for (const file of files.slice(0, 5)) {
    const filePath = path.join(dealDir, sanitizeFileName(file.name));
    const buffer = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(filePath, buffer);
  }

  await saveDealMeta(dealId, {
    deal_id: dealId,
    display_name: dealName.trim(),
    is_example: false,
    visibility: "private",
    source: "upload",
  });

  return getDealDetail(dealId);
}

export async function runDealPipeline(dealId, { phase = "extract", maxChunks = 5 } = {}) {
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
  return result;
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

  return documents.sort((a, b) => a.fileName.localeCompare(b.fileName));
}

export async function getDealDocumentResponse(dealId, requestedFileName) {
  const documents = await getDealDocuments(dealId);
  const document = documents.find((item) => item.fileName === requestedFileName);
  if (!document) {
    return null;
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
  if (!workbookPath) {
    return null;
  }

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

export async function getExtractionMetadata(dealId) {
  const metadataPath = path.join(NORMALIZED_ROOT, `${dealId}_extraction_metadata.json`);
  if (!(await exists(metadataPath))) {
    return null;
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
    return null;
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
