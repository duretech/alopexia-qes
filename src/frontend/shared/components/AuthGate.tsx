"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import type { PortalKind } from "../lib/session";
import { getSession } from "../lib/session";
import { Spinner } from "./Spinner";

export function AuthGate({
  portal,
  children,
}: {
  portal: PortalKind;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (pathname === "/login") {
      setReady(true);
      setOk(true);
      return;
    }
    const s = getSession(portal);
    if (!s?.token) {
      router.replace("/login");
      setReady(true);
      setOk(false);
      return;
    }
    setReady(true);
    setOk(true);
  }, [pathname, portal, router]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!ready || !ok) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spinner label="Checking session…" />
      </div>
    );
  }

  return <>{children}</>;
}
