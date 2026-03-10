import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { ManualDealForm } from "@/components/manual-deal-form";
import { UploadDealForm } from "@/components/upload-deal-form";

export default function NewDealPage({ searchParams }) {
  const mode = searchParams?.mode === "manual" ? "manual" : "upload";

  return (
    <AppShell
      eyebrow="New Deal"
      title="Create a fresh LBO case."
      description="Choose between document upload and direct number entry. Both paths land on the same review screen, where you can accept suggestions or override anything before analysis."
    >
      <section className="panel">
        <div className="panel-inner">
          <div className="hero-actions section-actions">
            <Link className={`override-button ${mode === "upload" ? "primary" : ""}`} href="/new?mode=upload">
              Upload documents
            </Link>
            <Link className={`override-button ${mode === "manual" ? "primary" : ""}`} href="/new?mode=manual">
              Enter numbers directly
            </Link>
          </div>
          {mode === "manual" ? <ManualDealForm /> : <UploadDealForm />}
        </div>
      </section>
    </AppShell>
  );
}
