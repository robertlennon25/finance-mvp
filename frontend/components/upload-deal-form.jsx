"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import {
  MAX_DOCUMENTS_PER_DEAL,
  MAX_SINGLE_FILE_BYTES,
  MAX_TOTAL_UPLOAD_BYTES,
  formatBytes
} from "@/lib/app-config";

export function UploadDealForm() {
  const router = useRouter();
  const [dealName, setDealName] = useState("");
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function onFileChange(event) {
    const selected = Array.from(event.target.files || []);
    setFiles(selected.slice(0, MAX_DOCUMENTS_PER_DEAL));
  }

  function submitForm() {
    setError("");

    if (!dealName.trim()) {
      setError("Enter a deal name.");
      return;
    }

    if (files.length === 0) {
      setError("Upload at least one document.");
      return;
    }

    startTransition(async () => {
      try {
        const formData = new FormData();
        formData.append("dealName", dealName.trim());
        files.forEach((file) => formData.append("documents", file));

        const response = await fetch("/api/deals", {
          method: "POST",
          body: formData
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Failed to create deal.");
        }

        router.push(`/deals/${payload.dealId}/process?phase=extract`);
      } catch (err) {
        setError(err.message || "Failed to create deal.");
      }
    });
  }

  return (
    <div className="upload-shell">
      <label className="field-label" htmlFor="deal-name">
        Deal name
      </label>
      <input
        className="text-input"
        id="deal-name"
        onChange={(event) => setDealName(event.target.value)}
        placeholder="Example: Expedia sponsor case"
        value={dealName}
      />

      <label className="field-label" htmlFor="documents">
        Documents (max {MAX_DOCUMENTS_PER_DEAL})
      </label>
      <input
        className="text-input"
        id="documents"
        multiple
        onChange={onFileChange}
        type="file"
      />

      <div className="upload-list">
        <p className="meta">
          Limits: {formatBytes(MAX_SINGLE_FILE_BYTES)} per file, {formatBytes(MAX_TOTAL_UPLOAD_BYTES)} total per deal.
        </p>
        {files.length === 0 ? (
          <p className="meta">No files selected yet.</p>
        ) : (
          files.map((file) => (
            <article className="candidate-card" key={`${file.name}-${file.size}`}>
              <strong>{file.name}</strong>
              <p>{Math.max(1, Math.round(file.size / 1024))} KB</p>
            </article>
          ))
        )}
      </div>

      <div className="hero-actions">
        <button className="override-button primary" disabled={isPending} onClick={submitForm} type="button">
          {isPending ? "Saving deal..." : "Upload and start pipeline"}
        </button>
      </div>
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}
