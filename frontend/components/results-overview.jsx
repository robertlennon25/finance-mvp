"use client";

import { useState } from "react";

const EXPLANATIONS = [
  {
    label: "Inputs",
    detail: "The app stores your documents, maps them to a deal, and prepares them for text extraction."
  },
  {
    label: "Extraction",
    detail: "Python ingests the files, chunks the text, and sends selected chunks to GPT-4.1 mini for structured field extraction."
  },
  {
    label: "Review",
    detail: "Extracted candidates are normalized, scored, and surfaced for user confirmation or override before model generation."
  },
  {
    label: "Excel",
    detail: "Resolved values feed the workbook builder, which populates assumptions, debt, returns, valuation, and checks tabs."
  },
  {
    label: "Checks",
    detail: "The pipeline reruns control steps and only then packages the final XLSX for download."
  }
];

export function ResultsOverview({ detail }) {
  const [active, setActive] = useState(EXPLANATIONS[0]);
  const summary = detail.workbookSummary;

  return (
    <section className="workspace">
      <div className="panel">
        <div className="panel-inner">
          <h2 className="section-title">Workbook Status</h2>
          <div className="summary-grid">
            <article className="stat-tile">
              <span>Deal</span>
              <strong>{detail.dealId}</strong>
            </article>
            <article className="stat-tile">
              <span>Company</span>
              <strong>{detail.companyName || "Unknown company"}</strong>
            </article>
            <article className="stat-tile">
              <span>Documents</span>
              <strong>{detail.documentCount}</strong>
            </article>
            <article className="stat-tile">
              <span>XLSX</span>
              <strong>{detail.workbookReady ? "Ready to download" : "Missing"}</strong>
            </article>
            <article className="stat-tile">
              <span>Extraction cache</span>
              <strong>
                {detail.extractionMetadata?.cache_hit_count
                  ? `Reused ${detail.extractionMetadata.cache_hit_count}x`
                  : detail.extractionMetadata
                    ? "Stored"
                    : "None"}
              </strong>
            </article>
          </div>
        </div>
      </div>

      {summary ? (
        <div className="panel">
          <div className="panel-inner">
            <h2 className="section-title">Key Outputs</h2>
            <div className="summary-grid">
              <article className="stat-tile">
                <span>Offer / Share</span>
                <strong>{formatMoney(summary.share_price_multiple)}</strong>
              </article>
              <article className="stat-tile">
                <span>Equity Value</span>
                <strong>{formatMoney(summary.equity_value_multiple)}</strong>
              </article>
              <article className="stat-tile">
                <span>Enterprise Value</span>
                <strong>{formatMoney(summary.enterprise_value_multiple)}</strong>
              </article>
              <article className="stat-tile">
                <span>MOIC / IRR</span>
                <strong>{formatMultiple(summary.moic)} / {formatPercent(summary.irr)}</strong>
              </article>
            </div>
            <div className="summary-grid summary-grid-secondary">
              <article className="stat-tile">
                <span>Entry Multiple</span>
                <strong>{formatMultiple(summary.entry_multiple)}</strong>
              </article>
              <article className="stat-tile">
                <span>Exit Multiple</span>
                <strong>{formatMultiple(summary.exit_multiple)}</strong>
              </article>
              <article className="stat-tile">
                <span>Entry / Exit Leverage</span>
                <strong>{formatMultiple(summary.entry_leverage)} / {formatMultiple(summary.exit_leverage)}</strong>
              </article>
              <article className="stat-tile">
                <span>Revenue CAGR</span>
                <strong>{formatPercent(summary.revenue_cagr)}</strong>
              </article>
            </div>
            {summary.warnings?.length ? (
              <div className="warning-stack">
                {summary.warnings.map((warning, index) => (
                  <p className="warning-text" key={`summary-warning-${index}`}>
                    {warning}
                  </p>
                ))}
                <p className="meta">
                  {summary.editable_note ||
                    "You can still update these values later directly in the Excel workbook."}
                </p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="panel">
        <div className="panel-inner">
          <h2 className="section-title">Pipeline Explained</h2>
          <div className="icon-step-grid">
            {EXPLANATIONS.map((item, index) => (
              <button
                className={`icon-step ${active.label === item.label ? "is-active" : ""}`}
                key={item.label}
                onClick={() => setActive(item)}
                type="button"
              >
                <span>{index + 1}</span>
                <strong>{item.label}</strong>
              </button>
            ))}
          </div>
          <div className="explanation-panel">
            <strong>{active.label}</strong>
            <p>{active.detail}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function formatMoney(value) {
  if (typeof value !== "number") {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  if (typeof value !== "number") {
    return "—";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatMultiple(value) {
  if (typeof value !== "number") {
    return "—";
  }
  return `${value.toFixed(1)}x`;
}
