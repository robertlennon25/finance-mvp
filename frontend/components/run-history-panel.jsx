export function RunHistoryPanel({ runHistory }) {
  const runs = runHistory?.runs ?? [];

  return (
    <section className="panel">
      <div className="panel-inner">
        <h2 className="section-title">Recent Runs</h2>
        {runs.length === 0 ? (
          <div className="empty-state">No pipeline runs recorded yet.</div>
        ) : (
          <div className="run-list">
            {runs.slice(0, 6).map((run, index) => (
              <article className="run-card" key={`${run.phase}-${run.run_at}-${index}`}>
                <strong>{run.phase === "analysis" ? "Analysis" : "Extraction"}</strong>
                <span className={`chip ${run.cached ? "good" : ""}`}>
                  {run.cached ? "cached" : "fresh"}
                </span>
                <p className="meta">{formatRunTime(run.run_at)}</p>
                <p className="meta">{run.message || run.status}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function formatRunTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value || "—";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}
