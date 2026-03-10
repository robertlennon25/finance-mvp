import { NextResponse } from "next/server";

import { createDealFromManualInputs } from "@/lib/server/deal-service";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function POST(request) {
  try {
    const payload = await request.json().catch(() => ({}));
    const dealName = String(payload.dealName || "").trim();
    const inputs = payload.inputs && typeof payload.inputs === "object" ? payload.inputs : {};

    if (!dealName) {
      return NextResponse.json({ error: "dealName is required." }, { status: 400 });
    }

    const user = await getAuthenticatedUser();
    const detail = await createDealFromManualInputs(dealName, inputs, user);
    return NextResponse.json({ ok: true, dealId: detail.dealId });
  } catch (error) {
    return NextResponse.json(
      { error: error?.message || "Failed to create deal from manual inputs." },
      { status: 500 }
    );
  }
}
