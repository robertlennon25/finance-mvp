import Link from "next/link";

import { AuthShell } from "@/components/auth-shell";
import {
  getSiteUrl,
  isSupabaseConfigured,
  isSupabasePersistenceConfigured
} from "@/lib/supabase/config";
import { getAuthenticatedUser } from "@/lib/supabase/server";

export async function AppShell({ eyebrow, title, description, children }) {
  const user = await getAuthenticatedUser();

  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <Link href="/">
            <strong>Finance AI MVP</strong>
          </Link>
          <nav className="topbar-nav">
            <Link href="/new">Start your LBO</Link>
            <Link href="/library">Existing LBOs</Link>
            <a href="https://github.com/robertlennon25/finance-mvp" rel="noreferrer" target="_blank">
              GitHub
            </a>
          </nav>
        </div>
      </header>

      <section className="hero">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="hero-copy">{description}</p>
      </section>

      <AuthShell
        isConfigured={isSupabaseConfigured()}
        persistenceConfigured={isSupabasePersistenceConfigured()}
        siteUrl={getSiteUrl()}
        user={user}
      />

      {children}
    </main>
  );
}
