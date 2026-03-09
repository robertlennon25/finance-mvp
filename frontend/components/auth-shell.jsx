import { GoogleAuthButton } from "@/components/google-auth-button";
import { SignOutButton } from "@/components/sign-out-button";

export function AuthShell({ isConfigured, persistenceConfigured, siteUrl, user }) {
  if (!isConfigured) {
    return (
      <section className="auth-banner">
        <div>
          <p className="auth-title">Supabase is not configured yet.</p>
          <p className="meta">
            Add the Supabase URL, anon key, service role key, and site URL to the frontend env
            before enabling Google sign-in and cloud override persistence.
          </p>
        </div>
      </section>
    );
  }

  if (!user) {
    return (
      <section className="auth-banner">
        <div>
          <p className="auth-title">Sign in to save overrides to Supabase.</p>
          <p className="meta">
            Local review payloads stay visible, but override writes are scoped to authenticated
            users.
          </p>
        </div>
        <GoogleAuthButton siteUrl={siteUrl} />
      </section>
    );
  }

  if (!persistenceConfigured) {
    return (
      <section className="auth-banner auth-banner-active">
        <div>
          <p className="auth-title">Signed in, but override persistence is not configured.</p>
          <p className="meta">
            Add `SUPABASE_SERVICE_ROLE_KEY` to enable saving user overrides to Supabase.
          </p>
        </div>
        <SignOutButton />
      </section>
    );
  }

  return (
    <section className="auth-banner auth-banner-active">
      <div>
        <p className="auth-title">Signed in</p>
        <p className="meta">{user.email || user.id}</p>
      </div>
      <SignOutButton />
    </section>
  );
}
