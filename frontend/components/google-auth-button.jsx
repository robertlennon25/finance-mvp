"use client";

import { useState, useTransition } from "react";

import { getSupabaseBrowserClient } from "@/lib/supabase/browser";

export function GoogleAuthButton({ siteUrl }) {
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function signIn() {
    setError("");
    startTransition(async () => {
      try {
        const supabase = getSupabaseBrowserClient();
        const { error: authError } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo: `${siteUrl}/auth/callback`
          }
        });

        if (authError) {
          throw authError;
        }
      } catch (err) {
        setError(err.message || "Failed to start Google sign-in.");
      }
    });
  }

  return (
    <div className="auth-actions">
      <button
        className="override-button primary"
        disabled={isPending}
        onClick={signIn}
        type="button"
      >
        {isPending ? "Redirecting..." : "Sign in with Google"}
      </button>
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}
