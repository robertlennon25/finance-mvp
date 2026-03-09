import Link from "next/link";

export function DocumentList({ dealId, documents }) {
  return (
    <section className="panel">
      <div className="panel-inner">
        <h2 className="section-title">Source Documents</h2>
        <p className="meta review-note">
          Documents are opened through application routes rather than direct filesystem paths so
          the same links can later resolve to Supabase Storage after Vercel deployment.
        </p>
        {documents.length === 0 ? (
          <div className="empty-state">No source documents found for this deal.</div>
        ) : (
          <div className="document-grid">
            {documents.map((document) => (
              <article className="document-card" key={`${document.bucket}-${document.fileName}`}>
                <strong>{document.fileName}</strong>
                <p className="meta">{document.bucket === "processed" ? "Processed copy" : "Inbox file"}</p>
                <div className="hero-actions">
                  <Link
                    className="override-button"
                    href={`/api/deals/${dealId}/documents/${encodeURIComponent(document.fileName)}`}
                    target="_blank"
                  >
                    View document
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
