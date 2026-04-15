"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Modal } from "@qes-ui/components/Modal";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

interface UserRecord {
  id: string;
  user_type: "doctor" | "pharmacy_user" | "admin_user";
  email: string;
  full_name: string;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  locked_until: string | null;
  created_at: string | null;
  // doctor-specific
  license_number?: string | null;
  // pharmacy-specific
  pharmacy_name?: string;
  pharmacy_license_number?: string | null;
  // admin-specific
  role?: string;
}

function userTypeTone(t: string): "success" | "warning" | "danger" | "neutral" {
  if (t === "doctor") return "success";
  if (t === "pharmacy_user") return "warning";
  if (t === "admin_user") return "danger";
  return "neutral";
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("");
  const [filterActive, setFilterActive] = useState<string>("");
  const [actionUser, setActionUser] = useState<UserRecord | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (filterType) params.set("user_type", filterType);
      if (filterActive !== "") params.set("is_active", filterActive);
      const res = await apiFetch("admin", `/api/v1/admin/users?${params}`);
      if (!res.ok) { setError("Could not load users."); return; }
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filterType, filterActive]);

  async function handleToggleActive(user: UserRecord) {
    setActionUser(user);
  }

  async function confirmToggle() {
    if (!actionUser) return;
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await apiFetch("admin", `/api/v1/admin/users/${actionUser.user_type}/${actionUser.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !actionUser.is_active }),
      });
      if (res.ok) {
        setUsers((prev) => prev.map((u) => u.id === actionUser.id ? { ...u, is_active: !actionUser.is_active } : u));
        setActionUser(null);
      } else {
        const err = await res.json();
        setActionError(formatApiError(err));
      }
    } catch {
      setActionError("Network error");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <Card padding="lg">
        <CardHeader
          title="User management"
          description="Manage doctors, pharmacy users, and admin accounts across the tenant."
          action={<Button variant="secondary" onClick={load}>Refresh</Button>}
        />

        {/* Filters */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
          <div className="qes-field" style={{ margin: 0, minWidth: "160px" }}>
            <label className="qes-label">User type</label>
            <select className="qes-input" value={filterType} onChange={(e: any) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              <option value="doctor">Doctors</option>
              <option value="pharmacy_user">Pharmacy users</option>
              <option value="admin_user">Admin users</option>
            </select>
          </div>
          <div className="qes-field" style={{ margin: 0, minWidth: "140px" }}>
            <label className="qes-label">Status</label>
            <select className="qes-input" value={filterActive} onChange={(e: any) => setFilterActive(e.target.value)}>
              <option value="">All</option>
              <option value="true">Active</option>
              <option value="false">Suspended</option>
            </select>
          </div>
        </div>

        {error && <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
            <Spinner label="Loading users…" />
          </div>
        ) : users.length === 0 ? (
          <EmptyState title="No users found" description="Try adjusting the filters." />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Type</th>
                  <th>Role / License</th>
                  <th>Status</th>
                  <th>MFA</th>
                  <th>Last login</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 500 }}>{u.full_name}</td>
                    <td style={{ fontSize: "0.875rem" }}>{u.email}</td>
                    <td><Badge tone={userTypeTone(u.user_type)}>{u.user_type.replace(/_/g, " ")}</Badge></td>
                    <td style={{ fontSize: "0.8125rem", color: "var(--color-neutral-500)" }}>
                      {u.role ?? u.license_number ?? u.pharmacy_name ?? "—"}
                    </td>
                    <td style={{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
                      <Badge tone={u.is_active ? "success" : "danger"}>
                        {u.is_active ? "Active" : "Suspended"}
                      </Badge>
                      {u.locked_until && new Date(u.locked_until) > new Date() && (
                        <Badge tone="warning">Locked</Badge>
                      )}
                    </td>
                    <td><Badge tone={u.mfa_enabled ? "success" : "neutral"}>{u.mfa_enabled ? "Enabled" : "Disabled"}</Badge></td>
                    <td style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString("es-ES") : "Never"}
                    </td>
                    <td>
                      <Button
                        variant={u.is_active ? "danger" : "secondary"}
                        onClick={() => handleToggleActive(u)}
                        style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}
                      >
                        {u.is_active ? "Suspend" : "Activate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Confirm action modal */}
      <Modal
        open={!!actionUser}
        title={actionUser?.is_active ? "Suspend user" : "Activate user"}
        onClose={() => { if (!actionLoading) { setActionUser(null); setActionError(null); } }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" disabled={actionLoading} onClick={() => setActionUser(null)}>Cancel</Button>
            <Button
              variant={actionUser?.is_active ? "danger" : "primary"}
              disabled={actionLoading}
              onClick={confirmToggle}
            >
              {actionLoading ? "Saving…" : actionUser?.is_active ? "Suspend" : "Activate"}
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: "0.9375rem", color: "var(--color-neutral-600)" }}>
          {actionUser?.is_active
            ? `Suspending ${actionUser?.full_name} will prevent them from logging in. This is recorded in the audit trail.`
            : `Reactivating ${actionUser?.full_name} will restore their access.`}
        </p>
        {actionError && <div className="qes-alert qes-alert--error" style={{ marginTop: "1rem" }}>{actionError}</div>}
      </Modal>
    </div>
  );
}
