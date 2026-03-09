import { NextResponse } from "next/server";

import {
  applyRecommendedEstimates,
  getDealDetail,
  getPipelineRunStatus,
  runDealPipeline
} from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function POST(request, { params }) {
  try {
    const user = await getAuthenticatedUser();
    const detail = await getDealDetail(params.dealId);
    if (!detail) {
      return NextResponse.json({ error: "Deal not found." }, { status: 404 });
    }

    const payload = await request.json().catch(() => ({}));
    const phase = payload.phase === "analysis" ? "analysis" : "extract";
    const applyEstimates = payload.applyEstimates === true;
    const maxChunks = Number.isFinite(Number(payload.maxChunks))
      ? Math.max(1, Math.min(8, Number(payload.maxChunks)))
      : 5;

    if (phase === "analysis" && applyEstimates && isSupabasePersistenceConfigured()) {
      if (user) {
        await applyRecommendedEstimates(params.dealId, user);
      }
    }

    const result = await runDealPipeline(params.dealId, {
      phase,
      maxChunks,
      userId: user?.id ?? null,
    });
    return NextResponse.json({ ok: true, phase, ...result });
  } catch (error) {
    console.error("Pipeline route failed", error);
    return NextResponse.json(
      { error: error?.message || "Pipeline execution failed." },
      { status: 500 }
    );
  }
}

export async function GET(request) {
  try {
    const jobId = request.nextUrl.searchParams.get("jobId");
    if (!jobId) {
      return NextResponse.json({ error: "Missing jobId." }, { status: 400 });
    }

    const result = await getPipelineRunStatus(jobId);
    if (!result) {
      return NextResponse.json({ error: "Worker polling is not configured." }, { status: 400 });
    }

    return NextResponse.json({ ok: true, ...result });
  } catch (error) {
    console.error("Pipeline status route failed", error);
    return NextResponse.json(
      { error: error?.message || "Failed to fetch pipeline status." },
      { status: 500 }
    );
  }
}
