import Link from "next/link";
import { notFound } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { DocumentList } from "@/components/document-list";
import { RunHistoryPanel } from "@/components/run-history-panel";
import { getDealDetail } from "@/lib/server/deal-service";

export default async function DealPage({ params }) {
  const detail = await getDealDetail(params.dealId);
  if (!detail) {
    notFound();
  }

  return (
    <AppShell
      eyebrow="Existing LBO"
      title={detail.companyName || detail.dealId}
      description="Inspect the source packet, then launch extraction when you want to start the model workflow."
    >
      <section className="workspace">
        <div className="panel">
          <div className="panel-inner">
            <h2 className="section-title">Deal Summary</h2>
            <div className="summary-grid">
              <article className="stat-tile">
                <span>Deal</span>
                <strong>{detail.dealId}</strong>
              </article>
              <article className="stat-tile">
                <span>Documents</span>
                <strong>{detail.documentCount}</strong>
              </article>
              <article className="stat-tile">
                <span>Review payload</span>
                <strong>{detail.hasReview ? "Ready" : "Not yet"}</strong>
              </article>
              <article className="stat-tile">
                <span>Workbook</span>
                <strong>{detail.workbookReady ? "Available" : "Not built"}</strong>
              </article>
              <article className="stat-tile">
                <span>AI cache</span>
                <strong>
                  {detail.extractionMetadata?.cache_hit_count
                    ? `Warm (${detail.extractionMetadata.cache_hit_count})`
                    : detail.extractionMetadata
                      ? "Primed"
                      : "Cold"}
                </strong>
              </article>
              <article className="stat-tile">
                <span>Visibility</span>
                <strong>{detail.meta?.is_example ? "Example deal" : "Private upload"}</strong>
              </article>
            </div>
            <div className="hero-actions section-actions">
              <Link className="override-button primary" href={`/deals/${detail.dealId}/process?phase=extract`}>
                Start this LBO
              </Link>
              {detail.hasReview ? (
                <Link className="override-button" href={`/deals/${detail.dealId}/review`}>
                  Open extracted inputs
                </Link>
              ) : null}
            </div>
          </div>
        </div>

        <DocumentList dealId={detail.dealId} documents={detail.documents} />
        <RunHistoryPanel runHistory={detail.runHistory} />
      </section>
    </AppShell>
  );
}
