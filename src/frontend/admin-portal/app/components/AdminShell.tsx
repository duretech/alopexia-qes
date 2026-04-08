"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useMemo } from "react";
import { AppShell, type NavItem } from "@qes-ui/components/AppShell";
import { apiFetch } from "@qes-ui/lib/api";
import { clearSession, getSession } from "@qes-ui/lib/session";

export function AdminShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = getSession("admin");

  const navItems: NavItem[] = useMemo(
    () => [
      {
        href: "/",
        label: "Overview",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        ),
      },
      {
        href: "/audit",
        label: "Audit export",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 3v12M8 11l4 4 4-4M4 21h16" />
          </svg>
        ),
      },
      {
        href: "/legal-holds",
        label: "Legal holds",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        ),
      },
      {
        href: "/deletions",
        label: "Deletions",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
          </svg>
        ),
      },
    ],
    [],
  );

  if (!session) {
    return null;
  }

  async function onLogout() {
    await apiFetch("admin", "/api/v1/auth/logout", { method: "POST" });
    clearSession("admin");
    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell
      portal="admin"
      portalLabel="Admin"
      navItems={navItems}
      user={session.user}
      onLogout={onLogout}
    >
      {children}
    </AppShell>
  );
}
