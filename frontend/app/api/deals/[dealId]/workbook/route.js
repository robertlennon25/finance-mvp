import { NextResponse } from "next/server";

import { getDealWorkbookResponse } from "@/lib/server/deal-service";

export async function GET(request, { params }) {
  const response = await getDealWorkbookResponse(params.dealId);
  if (!response) {
    return NextResponse.json({ error: "Workbook not found." }, { status: 404 });
  }

  return new NextResponse(response.body, {
    headers: response.headers
  });
}
