"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch } from "@qes-ui/lib/api";

interface HealthStats {
  prescriptions: { total: number; pending_verification: number; verified: number; failed: number };
  verifications: { by_status: Record<string, number> };
  compliance: { open_incidents: number; active_legal_holds: number; pending_deletion_requests: number };
  audit: { events_last_24h: number };
}

function QuickLink({ href, title, description, badge }: { href: string; title: string; description: string; badge?: { label: string; tone: "success" | "warning" | "danger" | "neutral" } }) {
  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      <div style={{ padding: "1.25rem 1.5rem", border: "1px solid var(--color-neutral-200)", borderRadius: "var(--radius-lg)", background: "white", cursor: "pointer", height: "100%", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--color-neutral-900)" }}>{title}</span>
          {badge && <Badge tone={badge.tone}>{badge.label}</Badge>}
        </div>
        <span style={{ fontSize: "0.875rem", color: "var(--color-neutral-500)", lineHeight: 1.4 }}>{description}</span>
      </div>
    </Link>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<HealthStats | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [statsRes, healthRes] = await Promise.all([
          apiFetch("admin", "/api/v1/admin/health/stats"),
          fetch("/health/live"),
        ]);
        setApiOk(healthRes.ok);
        if (statsRes.ok) setStats(await statsRes.json());
      } catch {
        setApiOk(false);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* System status */}
      <Card padding="lg">
        <CardHeader title="System overview" description="Admin and compliance control panel." />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
          {[
            { label: "API", value: apiOk === null ? "—" : apiOk ? "Operational" : "Degraded", tone: apiOk === null ? "neutral" as const : apiOk ? "success" as const : "danger" as const },
            { label: "Prescriptions", value: loading ? "…" : String(stats?.prescriptions.total ?? 0), tone: "neutral" as const },
            { label: "Verified", value: loading ? "…" : String(stats?.prescriptions.verified ?? 0), tone: "neutral" as const },
            { label: "Open incidents", value: loading ? "…" : String(stats?.compliance.open_incidents ?? 0), tone: (stats?.compliance.open_incidents ?? 0) > 0 ? "danger" as const : "neutral" as const },
          ].map(({ label, value, tone }) => (
            <div key={label} style={{ padding: "1rem 1.25rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.375rem" }}>{label}</div>
              {loading && label !== "API" ? (
                <Spinner label="" />
              ) : (
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: tone === "danger" ? "var(--color-danger-600)" : tone === "success" ? "var(--color-success-600)" : "var(--color-neutral-900)" }}>
                  {value}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Compliance alerts */}
      {!loading && stats && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {stats.compliance.open_incidents > 0 && (
            <div className="qes-alert qes-alert--error" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{stats.compliance.open_incidents} open incident{stats.compliance.open_incidents !== 1 ? "s" : ""} require attention.</span>
              <Link href="/incidents"><Button variant="secondary" style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}>View incidents</Button></Link>
            </div>
          )}
        </div>
      )}

      {/* Compliance quick links */}
      <Card padding="lg">
        <CardHeader title="Compliance operations" />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <QuickLink href="/audit-explorer" title="Audit event explorer" description="Search and filter the immutable hash-chained audit log with full details." />
          <QuickLink href="/audit" title="Audit export" description="Export audit events as JSON Lines for SIEM or external audit tools." />
          <QuickLink href="/incidents" title="Incident management" description="Track, investigate, and resolve security and compliance incidents." badge={stats?.compliance.open_incidents ? { label: `${stats.compliance.open_incidents} open`, tone: "danger" } : undefined} />
          <QuickLink href="/verifications" title="Verification results" description="View QTSP verification outcomes for all prescriptions in the tenant." />
          <QuickLink href="/suspicious-events" title="Suspicious events" description="High-severity and failure audit events requiring compliance review." />
          <QuickLink href="/evidence" title="Evidence export" description="Download QTSP validation reports and evidence artifacts for audit." />
        </div>
      </Card>

      <Card padding="lg">
        <CardHeader title="Administration" />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <QuickLink href="/users" title="User management" description="Manage doctors, pharmacy users, and admin accounts. Suspend or activate." />
          <QuickLink href="/legal-holds" title="Legal holds" description="Place and release legal holds preventing deletion of records." badge={stats?.compliance.active_legal_holds ? { label: `${stats.compliance.active_legal_holds} active`, tone: "warning" } : undefined} />
          <QuickLink href="/deletions" title="Deletion requests" description="Dual-approval deletion workflow for GDPR and data lifecycle management." badge={stats?.compliance.pending_deletion_requests ? { label: `${stats.compliance.pending_deletion_requests} pending`, tone: "warning" } : undefined} />
          <QuickLink href="/health" title="System health" description="Full system health dashboard with prescription and verification stats." />
        </div>
      </Card>
    </div>
  );
}
