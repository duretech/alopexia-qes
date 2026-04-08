"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@qes-ui/components/Badge";
import { Card } from "@qes-ui/components/Card";
import { Spinner } from "@qes-ui/components/Spinner";

export default function AdminDashboard() {
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/health/live")
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1 style={{ margin: "0 0 0.35rem", fontSize: "1.5rem", fontWeight: 600, letterSpacing: "-0.02em" }}>
          Dashboard
        </h1>
        <p style={{ margin: 0, color: "var(--neutral-500)", fontSize: "0.9375rem" }}>
          Operational snapshot and shortcuts for compliance workflows.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: "1rem",
        }}
      >
        <Card padding="lg">
          <div style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", color: "var(--neutral-500)", letterSpacing: "0.06em" }}>
            API status
          </div>
          {loading ? (
            <div style={{ marginTop: "1rem" }}>
              <Spinner label="Checking…" />
            </div>
          ) : (
            <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Badge tone={health ? "success" : "danger"}>{health ? "Online" : "Unreachable"}</Badge>
              <span style={{ fontSize: "0.875rem", color: "var(--neutral-600)" }}>/health/live</span>
            </div>
          )}
        </Card>

        <DashboardLink href="/audit" title="Audit export" description="JSON Lines export for external tooling." />
        <DashboardLink href="/legal-holds" title="Legal holds" description="Place and release holds on resources." />
        <DashboardLink href="/deletions" title="Deletion requests" description="Dual-approval deletion workflow." />
      </div>
    </div>
  );
}

function DashboardLink({ href, title, description }: { href: string; title: string; description: string }) {
  return (
    <Link href={href} style={{ textDecoration: "none", color: "inherit" }}>
      <Card padding="lg" className="qes-dash-card">
        <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--neutral-900)" }}>{title}</div>
        <p style={{ margin: "0.35rem 0 0", fontSize: "0.875rem", color: "var(--neutral-500)", lineHeight: 1.5 }}>
          {description}
        </p>
        <span style={{ display: "inline-block", marginTop: "0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "var(--accent-600)" }}>
          Open →
        </span>
      </Card>
    </Link>
  );
}
