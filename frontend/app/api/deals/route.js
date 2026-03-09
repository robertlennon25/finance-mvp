import { NextResponse } from "next/server";

import {
  MAX_DOCUMENTS_PER_DEAL,
  MAX_SINGLE_FILE_BYTES,
  MAX_TOTAL_UPLOAD_BYTES,
  formatBytes
} from "@/lib/app-config";
import { createDealFromUploads } from "@/lib/server/deal-service";

export async function POST(request) {
  try {
    const formData = await request.formData();
    const dealName = String(formData.get("dealName") || "").trim();
    const documents = formData
      .getAll("documents")
      .filter((file) => file && typeof file.name === "string" && file.size > 0);

    if (!dealName) {
      return NextResponse.json({ error: "dealName is required." }, { status: 400 });
    }

    if (documents.length === 0) {
      return NextResponse.json({ error: "At least one document is required." }, { status: 400 });
    }

    if (documents.length > MAX_DOCUMENTS_PER_DEAL) {
      return NextResponse.json(
        { error: `Upload limit is ${MAX_DOCUMENTS_PER_DEAL} documents.` },
        { status: 400 }
      );
    }

    const oversizedFile = documents.find((file) => file.size > MAX_SINGLE_FILE_BYTES);
    if (oversizedFile) {
      return NextResponse.json(
        {
          error: `${oversizedFile.name} exceeds the single-file limit of ${formatBytes(MAX_SINGLE_FILE_BYTES)}.`
        },
        { status: 400 }
      );
    }

    const totalBytes = documents.reduce((sum, file) => sum + (file.size || 0), 0);
    if (totalBytes > MAX_TOTAL_UPLOAD_BYTES) {
      return NextResponse.json(
        {
          error: `Total upload size exceeds the per-deal limit of ${formatBytes(MAX_TOTAL_UPLOAD_BYTES)}.`
        },
        { status: 400 }
      );
    }

    const detail = await createDealFromUploads(dealName, documents);
    return NextResponse.json({ ok: true, dealId: detail.dealId });
  } catch (error) {
    return NextResponse.json(
      { error: error?.message || "Failed to create deal from uploads." },
      { status: 500 }
    );
  }
}
