import Link from "next/link";

import { AppShell } from "@/components/app-shell";

export default function HomePage() {
  return (
    <AppShell
      eyebrow="Finance AI MVP"
      title="Start your LBO."
      description="Upload a small deal packet or open an existing case, run document extraction, review overrides, and generate a downloadable institutional workbook."
    >
      <section className="landing-grid">
        <article className="feature-card feature-card-primary">
          <p className="eyebrow">Path 01</p>
          <h2>Start your LBO</h2>
          <p>
            Upload up to five documents, trigger extraction, review inferred inputs, and run the
            model end to end.
          </p>
          <div className="hero-actions">
            <Link className="override-button primary" href="/new">
              Start your LBO
            </Link>
          </div>
        </article>

        <article className="feature-card">
          <p className="eyebrow">Path 02</p>
          <h2>Pick an existing LBO</h2>
          <p>
            Open a preloaded deal, inspect the supporting documents, and start the pipeline when
            you are ready.
          </p>
          <div className="hero-actions">
            <Link className="override-button" href="/library">
              Browse existing LBOs
            </Link>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-inner">
          <h2 className="section-title">Pipeline</h2>
          <div className="pipeline-preview">
            <article className="workflow-step">
              <strong>1. Upload or pick</strong>
              <span>Bring in a live packet or reuse a saved case.</span>
            </article>
            <article className="workflow-step">
              <strong>2. Extract</strong>
              <span>Read files, chunk text, run GPT-4.1 mini, normalize outputs.</span>
            </article>
            <article className="workflow-step">
              <strong>3. Review</strong>
              <span>Verify extracted fields, accept top candidates, or override anything.</span>
            </article>
            <article className="workflow-step">
              <strong>4. Analyze</strong>
              <span>Populate Excel, run checks, and package the workbook.</span>
            </article>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
