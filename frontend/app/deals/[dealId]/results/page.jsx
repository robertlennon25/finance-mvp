import Link from "next/link";
import { notFound } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { ResultsOverview } from "@/components/results-overview";
import { RunHistoryPanel } from "@/components/run-history-panel";
import { getDealDetail } from "@/lib/server/deal-service";

export default async function DealResultsPage({ params }) {
  const detail = await getDealDetail(params.dealId);
  if (!detail) {
    notFound();
  }

  return (
    <AppShell
      eyebrow="Results"
      title={`Final workbook for ${detail.companyName || detail.dealId}`}
      description="Download the model, inspect the pipeline steps, and revisit the review screen if you want to refine inputs."
    >
      <div className="hero-actions section-actions">
        <Link className="override-button" href={`/deals/${detail.dealId}/review`}>
          Revisit overrides
        </Link>
        <Link className="override-button primary" href={`/api/deals/${detail.dealId}/workbook`}>
          Download XLSX
        </Link>
      </div>
      <ResultsOverview detail={detail} />
      <RunHistoryPanel runHistory={detail.runHistory} />
    </AppShell>
  );
}
