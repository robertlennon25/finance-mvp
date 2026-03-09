"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function ApplyEstimatesButton({ dealId, disabled = false }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  function applyEstimates() {
    setError("");
    setMessage("");

    startTransition(async () => {
      try {
        const response = await fetch(`/api/deals/${dealId}/estimates`, {
          method: "POST",
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Failed to apply estimates.");
        }
        setMessage(
          payload.appliedCount > 0
            ? `Applied ${payload.appliedCount} reasonable estimate${payload.appliedCount === 1 ? "" : "s"}.`
            : "No recommended estimates were available."
        );
        router.refresh();
      } catch (err) {
        setError(err.message || "Failed to apply estimates.");
      }
    });
  }

  return (
    <div className="estimate-action">
      <button
        className="override-button"
        disabled={disabled || isPending}
        onClick={applyEstimates}
        type="button"
      >
        {isPending ? "Applying..." : "Use reasonable estimates"}
      </button>
      {message ? <p className="meta">{message}</p> : null}
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}
