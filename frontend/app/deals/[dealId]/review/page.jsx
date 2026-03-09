import Link from "next/link";
import { notFound } from "next/navigation";

import { ApplyEstimatesButton } from "@/components/apply-estimates-button";
import { AppShell } from "@/components/app-shell";
import { ReviewWorkspace } from "@/components/review-workspace";
import { getDealWorkspace } from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export default async function DealReviewPage({ params }) {
  const user = await getAuthenticatedUser();
  const workspace = await getDealWorkspace(
    params.dealId,
    user && isSupabasePersistenceConfigured() ? user : null
  );

  if (!workspace) {
    notFound();
  }

  return (
    <AppShell
      eyebrow="Review"
      title={`Review extracted inputs for ${workspace.companyName}`}
      description="Confirm the extracted values, apply any overrides you want, or skip directly to analysis."
    >
      <div className="hero-actions section-actions">
        <Link
          className="override-button primary"
          href={`/deals/${workspace.dealId}/process?phase=analysis${
            user && isSupabasePersistenceConfigured() ? "&applyEstimates=1" : ""
          }`}
        >
          Ready, perform analysis
        </Link>
        <ApplyEstimatesButton
          dealId={workspace.dealId}
          disabled={!(user && isSupabasePersistenceConfigured())}
        />
        <Link className="override-button" href={`/deals/${workspace.dealId}`}>
          Back to documents
        </Link>
      </div>
      <ReviewWorkspace workspace={workspace} user={user && isSupabasePersistenceConfigured() ? user : null} />
    </AppShell>
  );
}
