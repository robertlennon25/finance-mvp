import { NextResponse } from "next/server";

import { applyRecommendedEstimates } from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function POST(request, { params }) {
  if (!isSupabasePersistenceConfigured()) {
    return NextResponse.json(
      { error: "Supabase override persistence is not configured." },
      { status: 503 }
    );
  }

  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const result = await applyRecommendedEstimates(params.dealId, user);
  return NextResponse.json({ ok: true, ...result });
}
