"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useMemo } from "react";
import { AppShell, type NavItem } from "@qes-ui/components/AppShell";
import { apiFetch } from "@qes-ui/lib/api";
import { clearSession, getSession } from "@qes-ui/lib/session";

export function DoctorShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = getSession("doctor");

  const navItems: NavItem[] = useMemo(
    () => [
      {
        href: "/",
        label: "Upload",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>
        ),
      },
      {
        href: "/prescriptions",
        label: "My prescriptions",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
          </svg>
        ),
      },
      {
        href: "/audit",
        label: "Audit trail",
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
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
    await apiFetch("doctor", "/api/v1/auth/logout", { method: "POST" });
    clearSession("doctor");
    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell
      portal="doctor"
      portalLabel="Doctor"
      navItems={navItems}
      user={session.user}
      onLogout={onLogout}
    >
      {children}
    </AppShell>
  );
}
