"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function PipelineRunner({ dealId, phase, steps, targetHref, title, applyEstimates = false }) {
  const router = useRouter();
  const [activeStep, setActiveStep] = useState(0);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    let stepIndex = 0;

    async function runPipeline() {
      setStatus("running");
      setError("");

      const interval = setInterval(() => {
        stepIndex = Math.min(stepIndex + 1, steps.length - 1);
        if (!cancelled) {
          setActiveStep(stepIndex);
        }
      }, 1200);

      try {
        const response = await fetch(`/api/deals/${dealId}/pipeline`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phase, applyEstimates })
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.error || "Pipeline execution failed.");
        }

        const payload = await response.json().catch(() => ({}));

        clearInterval(interval);
        if (!cancelled) {
          setActiveStep(steps.length - 1);
          setStatus("done");
          setStatusMessage(payload.message || "");
          window.setTimeout(() => router.push(targetHref), 1100);
        }
      } catch (err) {
        clearInterval(interval);
        if (!cancelled) {
          setStatus("error");
          setError(err.message || "Pipeline execution failed.");
        }
      }
    }

    runPipeline();
    return () => {
      cancelled = true;
    };
  }, [applyEstimates, dealId, phase, router, steps, targetHref]);

  const progress = Math.round(((activeStep + 1) / steps.length) * 100);

  return (
    <section className="panel">
      <div className="panel-inner loading-shell">
        <div className="progress-ring">
          <div className="progress-ring-inner">
            <strong>{progress}%</strong>
            <span>{status === "done" ? "Done" : "Running"}</span>
          </div>
        </div>

        <div className="loading-copy">
          <h2>{title}</h2>
          <p className="meta">
            {status === "error"
              ? error
              : statusMessage ||
                "This local version runs the backend pipeline synchronously, then redirects when the next screen is ready."}
          </p>
          <div className="loading-steps">
            {steps.map((step, index) => (
              <article
                className={`loading-step ${index <= activeStep ? "is-active" : ""}`}
                key={step}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{step}</strong>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
