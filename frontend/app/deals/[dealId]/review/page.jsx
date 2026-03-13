import Link from "next/link";
import { notFound } from "next/navigation";

import { ApplyEstimatesButton } from "@/components/apply-estimates-button";
import { AppShell } from "@/components/app-shell";
import { ReviewWorkspace } from "@/components/review-workspace";
import { getDealWorkspace } from "@/lib/server/deal-service";
import { isSupabasePersistenceConfigured } from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function DealReviewPage({ params }) {
  const supabaseEnabled = isSupabasePersistenceConfigured();
  const user = supabaseEnabled ? await getAuthenticatedUser() : null;
  const workspace = await getDealWorkspace(
    params.dealId,
    user && supabaseEnabled ? user : null
  );

  if (!workspace) {
    notFound();
  }

  const canOverride = !supabaseEnabled || Boolean(user);

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
            user && supabaseEnabled ? "&applyEstimates=1" : ""
          }`}
        >
          Ready, perform analysis
        </Link>
        <ApplyEstimatesButton
          dealId={workspace.dealId}
          disabled={!(user && supabaseEnabled)}
        />
        <Link className="override-button" href={`/deals/${workspace.dealId}`}>
          Back to documents
        </Link>
      </div>
      <ReviewWorkspace workspace={workspace} user={user} canOverride={canOverride} />
    </AppShell>
  );
}
