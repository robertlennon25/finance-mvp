import { AppShell } from "@/components/app-shell";
import { DealGallery } from "@/components/deal-gallery";
import { getExampleDeals } from "@/lib/server/deal-service";

export default async function LibraryPage() {
  const deals = await getExampleDeals();

  return (
    <AppShell
      eyebrow="Existing Deals"
      title="Pick an existing LBO."
      description="Open a stored example case, inspect the output workbook, and review the supporting source documents separately from the live upload pipeline."
    >
      <DealGallery deals={deals} />
    </AppShell>
  );
}
