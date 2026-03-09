"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { formatFieldValue } from "@/lib/formatters";

export function OverrideForm({
  dealId,
  fieldName,
  selectedValue,
  overrideValue,
  topOptionValue,
  topOptionLabel = "Use Top Candidate",
  disabled = false
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [draftValue, setDraftValue] = useState(
    overrideValue !== undefined ? stringifyValue(overrideValue) : stringifyValue(selectedValue)
  );
  const [error, setError] = useState("");

  function submitOverride(nextValue) {
    setError("");
    startTransition(async () => {
      try {
        const response = await fetch(`/api/deals/${dealId}/overrides`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fieldName,
            value: nextValue
          })
        });
        if (!response.ok) {
          throw new Error("Failed to save override.");
        }
        router.refresh();
      } catch (err) {
        setError(err.message);
      }
    });
  }

  function clearOverride() {
    setError("");
    startTransition(async () => {
      try {
        const response = await fetch(
          `/api/deals/${dealId}/overrides?fieldName=${encodeURIComponent(fieldName)}`,
          { method: "DELETE" }
        );
        if (!response.ok) {
          throw new Error("Failed to clear override.");
        }
        router.refresh();
      } catch (err) {
        setError(err.message);
      }
    });
  }

  return (
    <div className="override-block">
      <textarea
        className="override-input"
        disabled={disabled}
        rows={3}
        value={draftValue}
        onChange={(event) => setDraftValue(event.target.value)}
      />
      <div className="override-actions">
        <button
          className="override-button primary"
          disabled={disabled || isPending}
          onClick={() => submitOverride(draftValue)}
          type="button"
        >
          {isPending ? "Saving..." : "Save Override"}
        </button>
        <button
          className="override-button"
          disabled={disabled || isPending}
          onClick={() => clearOverride()}
          type="button"
        >
          Clear
        </button>
        {topOptionValue !== undefined ? (
          <button
            className="override-button"
            disabled={disabled || isPending}
            onClick={() => {
              const value = stringifyValue(topOptionValue);
              setDraftValue(value);
              submitOverride(value);
            }}
            type="button"
          >
            {topOptionLabel}
          </button>
        ) : null}
      </div>
      <p className="meta">Current draft: {formatFieldValue(parseLooseValue(draftValue))}</p>
      {disabled ? (
        <p className="meta">Override editing is available after Google sign-in.</p>
      ) : null}
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}

function stringifyValue(value) {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

function parseLooseValue(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
