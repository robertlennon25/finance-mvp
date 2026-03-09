"use client";

import { useState, useTransition } from "react";

import { getSupabaseBrowserClient } from "@/lib/supabase/browser";

export function SignOutButton() {
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function signOut() {
    setError("");
    startTransition(async () => {
      try {
        const supabase = getSupabaseBrowserClient();
        const { error: authError } = await supabase.auth.signOut();
        if (authError) {
          throw authError;
        }
        window.location.href = "/";
      } catch (err) {
        setError(err.message || "Failed to sign out.");
      }
    });
  }

  return (
    <div className="auth-actions">
      <button className="override-button" disabled={isPending} onClick={signOut} type="button">
        {isPending ? "Signing out..." : "Sign out"}
      </button>
      {error ? <p className="meta error-text">{error}</p> : null}
    </div>
  );
}
