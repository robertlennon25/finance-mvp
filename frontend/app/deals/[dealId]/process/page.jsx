import { notFound } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { PipelineRunner } from "@/components/pipeline-runner";
import { getDealDetail } from "@/lib/server/deal-service";

const PHASE_CONFIG = {
  extract: {
    title: "Starting your LBO.",
    description: "Reading inputs, chunking documents, extracting fields, and preparing the override screen.",
    targetPath: "review",
    buttonLabel: "Run extraction pipeline",
    steps: [
      "Reading uploaded inputs",
      "Chunking documents",
      "Extracting with GPT-4.1 mini",
      "Normalizing values",
      "Preparing review payload"
    ]
  },
  analysis: {
    title: "Running analysis.",
    description: "Applying overrides, populating the workbook, and running safety checks.",
    targetPath: "results",
    buttonLabel: "Perform analysis",
    steps: [
      "Applying user overrides",
      "Resolving final model inputs",
      "Populating Excel workbook",
      "Double-checking outputs",
      "Packaging the final XLSX"
    ]
  }
};

export default async function DealProcessPage({ params, searchParams }) {
  const detail = await getDealDetail(params.dealId);
  if (!detail) {
    notFound();
  }

  const phase = searchParams?.phase === "analysis" ? "analysis" : "extract";
  const applyEstimates = searchParams?.applyEstimates === "1";
  const config = PHASE_CONFIG[phase];

  return (
    <AppShell eyebrow="Pipeline" title={config.title} description={config.description}>
      <PipelineRunner
        applyEstimates={applyEstimates}
        dealId={detail.dealId}
        phase={phase}
        steps={config.steps}
        targetHref={`/deals/${detail.dealId}/${config.targetPath}`}
        title={config.buttonLabel}
      />
    </AppShell>
  );
}
