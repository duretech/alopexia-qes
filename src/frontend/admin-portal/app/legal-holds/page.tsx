"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { Lock, Plus, Unlock, Inbox } from "lucide-react";

interface LegalHold {
  id: string;
  target_type: string;
  target_id: string;
  reason: string;
  reference_number: string | null;
  placed_at: string;
  is_active: boolean;
}

export default function LegalHoldsPage() {
  const [holds, setHolds] = useState<LegalHold[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetType, setTargetType] = useState("prescription");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const { toast } = useToast();

  async function fetchHolds() {
    try {
      const res = await fetch("/api/v1/admin/legal-holds");
      if (res.ok) setHolds(await res.json());
    } catch {
      toast("error", "Failed to load legal holds");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchHolds(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch("/api/v1/admin/legal-holds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_type: targetType, target_id: targetId, reason }),
      });
      if (res.ok) {
        toast("success", "Legal hold placed successfully");
        setTargetId("");
        setReason("");
        setShowForm(false);
        fetchHolds();
      } else {
        toast("error", "Failed to create legal hold");
      }
    } catch {
      toast("error", "Network error");
    } finally {
      setCreating(false);
    }
  }

  async function handleRelease(holdId: string) {
    const releaseReason = prompt("Release reason:");
    if (!releaseReason) return;
    try {
      const res = await fetch(`/api/v1/admin/legal-holds/${holdId}/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ release_reason: releaseReason }),
      });
      if (res.ok) {
        toast("success", "Legal hold released");
        fetchHolds();
      } else {
        toast("error", "Failed to release hold");
      }
    } catch {
      toast("error", "Network error");
    }
  }

  const activeCount = holds.filter((h) => h.is_active).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Legal Holds</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Manage legal holds to prevent data deletion during investigations.
          </p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          icon={showForm ? undefined : <Plus className="h-4 w-4" />}
          variant={showForm ? "secondary" : "primary"}
        >
          {showForm ? "Cancel" : "Place Hold"}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Lock className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Active Holds</p>
            <p className="text-lg font-semibold text-text-primary">{activeCount}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-slate-100 flex items-center justify-center">
            <Unlock className="h-5 w-5 text-slate-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Total (incl. released)</p>
            <p className="text-lg font-semibold text-text-primary">{holds.length}</p>
          </div>
        </div>
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Place Legal Hold</CardTitle>
            <CardDescription>
              A legal hold prevents deletion of the target resource and all associated data.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-primary">Target Type</label>
                <select
                  value={targetType}
                  onChange={(e) => setTargetType(e.target.value)}
                  className="block w-full h-9 px-3 rounded-lg border border-border text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                >
                  <option value="prescription">Prescription</option>
                  <option value="patient">Patient</option>
                  <option value="audit_event">Audit Event</option>
                </select>
              </div>
              <Input
                label="Target ID"
                type="text"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="UUID"
                required
              />
              <Input
                label="Reason"
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Legal investigation #..."
                required
              />
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={creating} icon={<Lock className="h-4 w-4" />}>
                Place Hold
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Table */}
      <Card padding={false}>
        {loading ? (
          <div className="p-6"><TableSkeleton rows={4} cols={5} /></div>
        ) : (
          <DataTable
            data={holds}
            keyExtractor={(h) => h.id}
            emptyMessage="No legal holds found."
            emptyIcon={<Inbox className="h-12 w-12" />}
            columns={[
              {
                key: "target",
                header: "Target",
                render: (h) => (
                  <div>
                    <Badge variant="default">{h.target_type}</Badge>
                    <span className="ml-2 font-mono text-xs text-text-secondary">{h.target_id.slice(0, 8)}...</span>
                  </div>
                ),
              },
              {
                key: "reason",
                header: "Reason",
                render: (h) => <span className="text-text-primary">{h.reason}</span>,
              },
              {
                key: "placed",
                header: "Placed",
                render: (h) => (
                  <span className="text-text-secondary text-xs">
                    {new Date(h.placed_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (h) => (
                  <Badge variant={h.is_active ? "success" : "default"} dot>
                    {h.is_active ? "Active" : "Released"}
                  </Badge>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                render: (h) => h.is_active ? (
                  <Button variant="danger" size="sm" onClick={() => handleRelease(h.id)} icon={<Unlock className="h-3.5 w-3.5" />}>
                    Release
                  </Button>
                ) : null,
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
