import { NextResponse } from "next/server";

import {
  clearDealOverride,
  saveDealOverride
} from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function POST(request, { params }) {
  const user = isSupabasePersistenceConfigured() ? await getAuthenticatedUser() : null;

  if (isSupabasePersistenceConfigured() && !user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { dealId } = params;
  const payload = await request.json();
  const fieldName = String(payload.fieldName || "").trim();
  const rawValue = payload.value;

  if (!fieldName) {
    return NextResponse.json({ error: "fieldName is required" }, { status: 400 });
  }

  const value = coerceOverrideValue(rawValue);
  const workspace = await saveDealOverride(dealId, fieldName, value, user);
  return NextResponse.json({ ok: true, workspace });
}

export async function DELETE(request, { params }) {
  const user = isSupabasePersistenceConfigured() ? await getAuthenticatedUser() : null;

  if (isSupabasePersistenceConfigured() && !user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { dealId } = params;
  const { searchParams } = new URL(request.url);
  const fieldName = String(searchParams.get("fieldName") || "").trim();

  if (!fieldName) {
    return NextResponse.json({ error: "fieldName is required" }, { status: 400 });
  }

  const workspace = await clearDealOverride(dealId, fieldName, user);
  return NextResponse.json({ ok: true, workspace });
}

function coerceOverrideValue(value) {
  if (typeof value !== "string") {
    return value;
  }

  const trimmed = value.trim();
  if (trimmed === "") {
    return "";
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const numeric = Number(trimmed);
    if (!Number.isNaN(numeric) && trimmed === String(numeric)) {
      return numeric;
    }
    return trimmed;
  }
}
