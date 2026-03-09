import { NextResponse } from "next/server";

import { getSiteUrl } from "@/lib/supabase/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const next = requestUrl.searchParams.get("next") || "/";
  const redirectUrl = new URL(next, getSiteUrl());

  if (!code) {
    return NextResponse.redirect(redirectUrl);
  }

  const supabase = await getSupabaseServerClient();
  if (!supabase) {
    return NextResponse.redirect(redirectUrl);
  }

  await supabase.auth.exchangeCodeForSession(code);
  return NextResponse.redirect(redirectUrl);
}
