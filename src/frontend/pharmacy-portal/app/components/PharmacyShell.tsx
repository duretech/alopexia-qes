"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useMemo } from "react";
import { AppShell, type NavItem } from "@qes-ui/components/AppShell";
import { apiFetch } from "@qes-ui/lib/api";
import { clearSession, getSession } from "@qes-ui/lib/session";

export function PharmacyShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = getSession("pharmacy");

  const navItems: NavItem[] = useMemo(
    () => [
      {
        href: "/",
        label: "Prescriptions",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" />
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
    await apiFetch("pharmacy", "/api/v1/auth/logout", { method: "POST" });
    clearSession("pharmacy");
    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell
      portal="pharmacy"
      portalLabel="Pharmacy"
      navItems={navItems}
      user={session.user}
      onLogout={onLogout}
    >
      {children}
    </AppShell>
  );
}
