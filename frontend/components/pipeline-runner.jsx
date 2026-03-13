"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

export function PipelineRunner({ dealId, phase, steps, targetHref, title, applyEstimates = false }) {
  const router = useRouter();
  const [activeStep, setActiveStep] = useState(0);
  const [progressPct, setProgressPct] = useState(5);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (hasStartedRef.current) {
      return;
    }
    hasStartedRef.current = true;

    let cancelled = false;
    let pollTimeoutId = null;

    async function runPipeline() {
      setStatus("running");
      setError("");
      setProgressPct(5);
      setActiveStep(0);

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
        if (payload.remote && payload.jobId) {
          if (!cancelled) {
            setStatusMessage(payload.message || "Pipeline job queued.");
            setProgressPct((current) => Math.max(current, 10));
          }
          await pollRemoteJob(payload.jobId);
          return;
        }

        if (!cancelled) {
          setActiveStep(steps.length - 1);
          setProgressPct(100);
          setStatus("done");
          setStatusMessage(payload.message || "");
          window.setTimeout(() => { router.refresh(); router.push(targetHref); }, 1100);
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setError(err.message || "Pipeline execution failed.");
        }
      }
    }

    async function pollRemoteJob(jobId) {
      async function pollOnce() {
        const response = await fetch(`/api/deals/${dealId}/pipeline?jobId=${encodeURIComponent(jobId)}`, {
          method: "GET",
          cache: "no-store",
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Failed to poll worker status.");
        }

        if (cancelled) {
          return;
        }

        if (typeof payload.progress === "number") {
          const boundedProgress = Math.max(5, Math.min(100, payload.progress));
          const mappedStep = Math.max(
            0,
            Math.min(steps.length - 1, Math.floor((boundedProgress / 100) * steps.length))
          );
          setActiveStep((current) => Math.max(current, mappedStep));
          setProgressPct((current) => Math.max(current, boundedProgress));
        }
        setStatusMessage(payload.message || "");

        if (payload.status === "completed") {
          setActiveStep(steps.length - 1);
          setProgressPct(100);
          setStatus("done");
          window.setTimeout(() => { router.refresh(); router.push(targetHref); }, 1100);
          return;
        }

        if (payload.status === "failed") {
          throw new Error(payload.message || "Pipeline execution failed.");
        }

        pollTimeoutId = window.setTimeout(pollOnce, 1800);
      }

      await pollOnce();
    }

    runPipeline();
    return () => {
      cancelled = true;
      if (pollTimeoutId) {
        window.clearTimeout(pollTimeoutId);
      }
    };
  }, [applyEstimates, dealId, phase, router, steps, targetHref]);

  return (
    <section className="panel">
      <div className="panel-inner loading-shell">
        <div className="progress-ring">
          <div className="progress-ring-inner">
            <strong>{progressPct}%</strong>
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
