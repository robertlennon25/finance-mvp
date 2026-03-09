import { OverrideForm } from "@/components/override-form";
import { formatFieldValue } from "@/lib/formatters";

export function ReviewWorkspace({ workspace, user }) {
  const fields = Object.entries(workspace.review.fields);
  const overrides = workspace.overrides ?? {};

  return (
    <section className="workspace">
      <div className="panel">
        <div className="panel-inner">
          <h2 className="section-title">Field Review</h2>
          {!user ? (
            <p className="meta review-note">
              Sign in with Google to persist overrides in Supabase. You can still inspect all
              extracted values before analysis.
            </p>
          ) : null}
          <table className="field-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Selected Value</th>
                <th>Source</th>
                <th>Options</th>
              </tr>
            </thead>
            <tbody>
              {fields.map(([fieldName, fieldState]) => {
                const selected = fieldState.selected;
                const options = fieldState.options ?? [];
                return (
                  <tr key={fieldName}>
                    <td className="field-name">{fieldName}</td>
                    <td className="field-value">
                      {formatFieldValue(selected?.value)}
                      <div className="chip-row">
                        <span
                          className={`chip ${
                            selected?.method === "user_override"
                              ? "warn"
                              : selected?.method === "estimated"
                                ? "warn"
                                : "good"
                          }`}
                        >
                          {selected?.method ?? "default"}
                        </span>
                        <span className="chip">
                          confidence {(selected?.confidence ?? 0).toFixed(2)}
                        </span>
                        {fieldState?.recommended_estimate ? (
                          <span className="chip warn">estimate available</span>
                        ) : null}
                      </div>
                      {fieldState?.warnings?.length ? (
                        <div className="warning-stack">
                          {fieldState.warnings.map((warning, index) => (
                            <p className="warning-text" key={`${fieldName}-warning-${index}`}>
                              {warning}
                            </p>
                          ))}
                        </div>
                      ) : null}
                    </td>
                    <td>
                      <div>{selected?.source_document_id ?? "default"}</div>
                      <p className="meta">{selected?.source_locator ?? ""}</p>
                      {selected?.source_urls?.length ? (
                        <div className="source-link-list">
                          {selected.source_urls.map((url, index) => (
                            <p className="meta" key={`${fieldName}-selected-url-${index}`}>
                              <a href={url} rel="noreferrer" target="_blank">
                                {url}
                              </a>
                            </p>
                          ))}
                        </div>
                      ) : null}
                      {selected?.normalization_notes?.length ? (
                        <p className="meta">{selected.normalization_notes.join(" ")}</p>
                      ) : null}
                    </td>
                    <td>
                      {options.length === 0 ? (
                        <span className="meta">No alternative candidates</span>
                      ) : (
                        <div className="candidate-list">
                          {options.slice(0, 3).map((option, index) => (
                            <article className="candidate-card" key={`${fieldName}-${index}`}>
                              <strong>{formatFieldValue(option.normalized_value ?? option.value)}</strong>
                              <div className="chip-row">
                                <span className={`chip ${option.method === "estimated" ? "warn" : ""}`}>
                                  {option.method}
                                </span>
                                <span className="chip">
                                  score {(option.selection_score ?? 0).toFixed(2)}
                                </span>
                                <span className="chip">
                                  conf {(option.confidence ?? 0).toFixed(2)}
                                </span>
                              </div>
                              <p>{option.source_locator}</p>
                              {option.source_urls?.length ? (
                                <div className="source-link-list">
                                  {option.source_urls.map((url, sourceIndex) => (
                                    <p className="meta" key={`${fieldName}-${index}-url-${sourceIndex}`}>
                                      <a href={url} rel="noreferrer" target="_blank">
                                        {url}
                                      </a>
                                    </p>
                                  ))}
                                </div>
                              ) : null}
                            </article>
                          ))}
                        </div>
                      )}
                      <OverrideForm
                        dealId={workspace.dealId}
                        fieldName={fieldName}
                        selectedValue={selected?.value}
                        overrideValue={overrides[fieldName]}
                        topOptionValue={
                          (fieldState?.recommended_estimate?.normalized_value ??
                            fieldState?.recommended_estimate?.value) ??
                          options[0]?.normalized_value ??
                          options[0]?.value
                        }
                        topOptionLabel={fieldState?.recommended_estimate ? "Use Estimate" : "Use Top Candidate"}
                        disabled={!user}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
