import { NextResponse } from "next/server";

import {
  applyRecommendedEstimates,
  getDealDetail,
  runDealPipeline
} from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function POST(request, { params }) {
  try {
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
      const user = await getAuthenticatedUser();
      if (user) {
        await applyRecommendedEstimates(params.dealId, user);
      }
    }

    const result = await runDealPipeline(params.dealId, { phase, maxChunks });
    return NextResponse.json({ ok: true, phase, ...result });
  } catch (error) {
    return NextResponse.json(
      { error: error?.message || "Pipeline execution failed." },
      { status: 500 }
    );
  }
}
