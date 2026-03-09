import { AppShell } from "@/components/app-shell";
import { DealGallery } from "@/components/deal-gallery";
import { getExampleDeals } from "@/lib/server/deal-service";

export default async function LibraryPage() {
  const deals = await getExampleDeals();

  return (
    <AppShell
      eyebrow="Existing Deals"
      title="Pick an existing LBO."
      description="Open a stored case, inspect its source files, and launch the workflow when you are ready."
    >
      <DealGallery deals={deals} />
    </AppShell>
  );
}
