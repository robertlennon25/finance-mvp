"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

const FIELDS = [
  { key: "company_name", label: "Company", type: "text", placeholder: "Expedia Group" },
  { key: "entry_year", label: "Entry year", type: "number", placeholder: "2024" },
  { key: "revenue", label: "Revenue", type: "number", placeholder: "13691000000" },
  { key: "ebitda", label: "EBITDA", type: "number", placeholder: "2934000000" },
  { key: "cash", label: "Cash", type: "number", placeholder: "4183000000" },
  { key: "debt", label: "Debt", type: "number", placeholder: "6266000000" },
  { key: "shares_outstanding", label: "Shares", type: "number", placeholder: "122530000" },
  { key: "entry_multiple", label: "Entry multiple", type: "number", placeholder: "10.5" },
  { key: "exit_multiple", label: "Exit multiple", type: "number", placeholder: "11.0" },
  { key: "tax_rate", label: "Tax rate", type: "number", placeholder: "0.25" },
  { key: "revenue_growth_assumption", label: "Rev growth", type: "number", placeholder: "0.05" },
  { key: "ebitda_margin_assumption", label: "EBITDA margin", type: "number", placeholder: "0.20" },
];

export function ManualDealForm() {
  const router = useRouter();
  const [dealName, setDealName] = useState("");
  const [values, setValues] = useState({});
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function setField(key, value) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function submitForm() {
    setError("");
    if (!dealName.trim()) {
      setError("Enter a deal name.");
      return;
    }

    startTransition(async () => {
      try {
        const response = await fetch("/api/deals/manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            dealName: dealName.trim(),
            inputs: Object.fromEntries(
              Object.entries(values).filter(([, value]) => String(value ?? "").trim() !== "")
            ),
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Failed to create manual-entry deal.");
        }
        router.push(`/deals/${payload.dealId}/review`);
      } catch (err) {
        setError(err.message || "Failed to create manual-entry deal.");
      }
    });
  }

  return (
    <div className="upload-shell">
      <label className="field-label" htmlFor="manual-deal-name">
        Deal name
      </label>
      <input
        className="text-input"
        id="manual-deal-name"
        onChange={(event) => setDealName(event.target.value)}
        placeholder="Example: Expedia direct-entry case"
        value={dealName}
      />

      <div className="compact-input-grid">
        {FIELDS.map((field) => (
          <label className="compact-field" htmlFor={`manual-${field.key}`} key={field.key}>
            <span className="field-label">{field.label}</span>
            <input
              className="text-input"
              id={`manual-${field.key}`}
              inputMode={field.type === "number" ? "decimal" : undefined}
              onChange={(event) => setField(field.key, event.target.value)}
              placeholder={field.placeholder}
              type={field.type === "number" ? "text" : field.type}
              value={values[field.key] ?? ""}
            />
          </label>
        ))}
      </div>

      <p className="meta review-note">
        Enter only what you know. Missing values will still go through the review screen, where the
        app can suggest reasonable estimates based on the numbers you do enter.
      </p>

      <div className="hero-actions">
        <button className="override-button primary" disabled={isPending} onClick={submitForm} type="button">
          {isPending ? "Creating case..." : "Create case from numbers"}
        </button>
      </div>
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}
