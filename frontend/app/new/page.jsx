import { AppShell } from "@/components/app-shell";
import { UploadDealForm } from "@/components/upload-deal-form";

export default function NewDealPage() {
  return (
    <AppShell
      eyebrow="New Deal"
      title="Create a fresh LBO case."
      description="Upload up to five documents. The app will save them, run the extraction pipeline, and bring you to the override review step."
    >
      <section className="panel">
        <div className="panel-inner">
          <UploadDealForm />
        </div>
      </section>
    </AppShell>
  );
}
