import { NextResponse } from "next/server";

import { getDealDocumentResponse } from "@/lib/server/deal-service";

export async function GET(request, { params }) {
  const response = await getDealDocumentResponse(params.dealId, params.fileName);
  if (!response) {
    return NextResponse.json({ error: "Document not found." }, { status: 404 });
  }

  return new NextResponse(response.body, {
    headers: response.headers
  });
}
