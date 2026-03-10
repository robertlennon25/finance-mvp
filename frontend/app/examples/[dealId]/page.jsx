import Link from "next/link";
import { notFound } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { DocumentList } from "@/components/document-list";
import { ResultsOverview } from "@/components/results-overview";
import { RunHistoryPanel } from "@/components/run-history-panel";
import { isCuratedExampleDeal } from "@/lib/example-deals";
import { getDealDetail } from "@/lib/server/deal-service";

export default async function ExampleDealPage({ params }) {
  const detail = await getDealDetail(params.dealId);
  const isExample =
    detail &&
    (isCuratedExampleDeal(params.dealId) ||
      detail.meta?.is_example ||
      detail.meta?.visibility === "public_example");
  if (!detail || !isExample) {
    notFound();
  }

  return (
    <AppShell
      eyebrow="Existing LBO"
      title={detail.companyName || detail.dealId}
      description="This is a stored example case. Review the outputs, download the workbook, and inspect the source documents that fed the model."
    >
      <div className="hero-actions section-actions">
        <Link className="override-button primary" href={`/api/deals/${detail.dealId}/workbook`}>
          Download XLSX
        </Link>
        {detail.hasReview ? (
          <Link className="override-button" href={`/deals/${detail.dealId}/review`}>
            View extracted inputs
          </Link>
        ) : null}
      </div>

      <ResultsOverview detail={detail} />
      <DocumentList dealId={detail.dealId} documents={detail.documents} />
      <RunHistoryPanel runHistory={detail.runHistory} />
    </AppShell>
  );
}
