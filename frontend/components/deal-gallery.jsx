import Link from "next/link";

export function DealGallery({ deals }) {
  if (!deals.length) {
    return (
      <section className="panel">
        <div className="panel-inner empty-state">
          No saved deals yet. Upload a new packet to create your first LBO case.
        </div>
      </section>
    );
  }

  return (
    <section className="card-grid">
      {deals.map((deal) => (
        <article className="feature-card" key={deal.dealId}>
          <p className="eyebrow">Stored deal</p>
          <h2>{deal.companyName || deal.dealId}</h2>
          <p className="meta">
            {deal.documentCount} docs · {deal.fieldCount} extracted fields ·{" "}
            {deal.workbookReady ? "workbook ready" : "workbook pending"}
          </p>
          {deal.extractionMetadata ? (
            <p className="meta">
              {deal.extractionMetadata.cache_hit_count
                ? `cache reused ${deal.extractionMetadata.cache_hit_count}x`
                : "cached extraction available"}
            </p>
          ) : null}
          <div className="hero-actions">
            <Link className="override-button primary" href={`/deals/${deal.dealId}/results`}>
              Open deal
            </Link>
          </div>
        </article>
      ))}
    </section>
  );
}
