"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch } from "@qes-ui/lib/api";

interface HealthStats {
  prescriptions: {
    by_status: Record<string, number>;
    total: number;
    pending_verification: number;
    verified: number;
    failed: number;
  };
  verifications: {
    by_status: Record<string, number>;
    pending_manual_review: number;
  };
  compliance: {
    open_incidents: number;
    active_legal_holds: number;
    pending_deletion_requests: number;
  };
  audit: {
    events_last_24h: number;
  };
  generated_at: string;
}

function StatCard({ label, value, tone, href }: { label: string; value: number | string; tone?: "success" | "warning" | "danger" | "neutral"; href?: string }) {
  const inner = (
    <div style={{ padding: "1.25rem 1.5rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)", cursor: href ? "pointer" : "default" }}>
      <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>{label}</div>
      <div style={{ fontSize: "1.75rem", fontWeight: 700, lineHeight: 1, color: tone === "danger" ? "var(--color-danger-600)" : tone === "warning" ? "var(--color-warning-600)" : "var(--color-neutral-900)" }}>
        {value}
      </div>
    </div>
  );
  if (href) return <Link href={href} style={{ textDecoration: "none" }}>{inner}</Link>;
  return inner;
}

export default function HealthPage() {
  const [stats, setStats] = useState<HealthStats | null>(null);
  const [apiHealth, setApiHealth] = useState<"ok" | "error" | "loading">("loading");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, healthRes] = await Promise.all([
        apiFetch("admin", "/api/v1/admin/health/stats"),
        fetch("/health/live"),
      ]);
      setApiHealth(healthRes.ok ? "ok" : "error");
      if (!statsRes.ok) { setError("Could not load health stats."); return; }
      setStats(await statsRes.json());
    } catch {
      setError("Network error");
      setApiHealth("error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600 }}>System health dashboard</h2>
            {stats && <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>Updated {new Date(stats.generated_at).toLocaleString("es-ES")}</p>}
          </div>
          <Button variant="secondary" onClick={load} disabled={loading}>Refresh</Button>
        </div>
      </Card>

      {error && <div className="qes-alert qes-alert--error">{error}</div>}

      {loading ? (
        <Card padding="lg"><div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Loading stats…" /></div></Card>
      ) : stats ? (
        <>
          {/* Service status */}
          <Card padding="lg">
            <CardHeader title="Service status" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>API</div>
                <Badge tone={apiHealth === "ok" ? "success" : "danger"}>{apiHealth === "ok" ? "Operational" : "Degraded"}</Badge>
              </div>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Database</div>
                <Badge tone="success">Connected</Badge>
              </div>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Audit log events (24h)</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{stats.audit.events_last_24h.toLocaleString()}</div>
              </div>
            </div>
          </Card>

          {/* Prescriptions */}
          <Card padding="lg">
            <CardHeader title="Prescriptions" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
              <StatCard label="Total" value={stats.prescriptions.total} />
              <StatCard label="Verified" value={stats.prescriptions.verified} tone="success" />
              <StatCard label="Pending verification" value={stats.prescriptions.pending_verification} tone={stats.prescriptions.pending_verification > 0 ? "warning" : "neutral"} />
              <StatCard label="Failed verification" value={stats.prescriptions.failed} tone={stats.prescriptions.failed > 0 ? "danger" : "neutral"} />
            </div>
            {Object.keys(stats.prescriptions.by_status).length > 0 && (
              <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {Object.entries(stats.prescriptions.by_status).map(([status, count]) => (
                  <div key={status} style={{ fontSize: "0.8125rem", padding: "0.25rem 0.625rem", background: "var(--color-neutral-100)", borderRadius: "var(--radius-sm)" }}>
                    {status.replace(/_/g, " ")}: <strong>{count}</strong>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Compliance */}
          <Card padding="lg">
            <CardHeader title="Compliance status" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
              <StatCard
                label="Pending manual review"
                value={stats.verifications.pending_manual_review}
                tone={stats.verifications.pending_manual_review > 0 ? "warning" : "neutral"}
                href="/verifications"
              />
              <StatCard
                label="Open incidents"
                value={stats.compliance.open_incidents}
                tone={stats.compliance.open_incidents > 0 ? "danger" : "neutral"}
                href="/incidents"
              />
              <StatCard
                label="Active legal holds"
                value={stats.compliance.active_legal_holds}
                tone={stats.compliance.active_legal_holds > 0 ? "warning" : "neutral"}
                href="/legal-holds"
              />
              <StatCard
                label="Pending deletions"
                value={stats.compliance.pending_deletion_requests}
                tone={stats.compliance.pending_deletion_requests > 0 ? "warning" : "neutral"}
                href="/deletions"
              />
            </div>
          </Card>

          {/* Verifications by status */}
          {Object.keys(stats.verifications.by_status).length > 0 && (
            <Card padding="lg">
              <CardHeader title="Verification status breakdown" />
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                {Object.entries(stats.verifications.by_status).map(([status, count]) => (
                  <div key={status} style={{ padding: "0.75rem 1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)", textAlign: "center", minWidth: "120px" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{count}</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginTop: "0.25rem" }}>{status}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
