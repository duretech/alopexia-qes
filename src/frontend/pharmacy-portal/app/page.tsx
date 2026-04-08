"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { Download, CheckCircle, RefreshCw, Inbox, Package } from "lucide-react";

interface Prescription {
  id: string;
  status: string;
  verification_status: string | null;
  dispensing_status: string | null;
  doctor_id: string;
  patient_id: string;
  created_at: string;
}

export default function PharmacyPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { toast } = useToast();

  async function fetchData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/pharmacy/prescriptions");
      if (res.ok) setPrescriptions(await res.json());
      else setError("Failed to load prescriptions");
    } catch {
      setError("Network error — is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchData(); }, []);

  async function handleDownload(id: string) {
    setActionLoading(id + "-dl");
    try {
      const res = await fetch(`/api/v1/pharmacy/prescriptions/${id}/download`);
      if (res.ok) {
        const data = await res.json();
        window.open(data.signed_url, "_blank");
      } else {
        toast("error", "Failed to generate download URL");
      }
    } catch {
      toast("error", "Network error");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDispense(id: string) {
    setActionLoading(id + "-disp");
    try {
      const res = await fetch(`/api/v1/pharmacy/prescriptions/${id}/dispense`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dispensing_status: "dispensed" }),
      });
      if (res.ok) {
        setPrescriptions((prev) =>
          prev.map((rx) => rx.id === id ? { ...rx, status: "dispensed", dispensing_status: "dispensed" } : rx)
        );
        toast("success", "Prescription dispensed successfully");
      } else {
        const err = await res.json().catch(() => ({}));
        toast("error", err.detail || "Dispensing failed");
      }
    } catch {
      toast("error", "Network error");
    } finally {
      setActionLoading(null);
    }
  }

  const verified = prescriptions.filter((rx) => rx.status === "verified" || rx.status === "available").length;
  const dispensed = prescriptions.filter((rx) => rx.status === "dispensed").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Prescriptions</h1>
          <p className="mt-1 text-sm text-text-secondary">View, download, and dispense verified prescriptions.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={fetchData} icon={<RefreshCw className="h-3.5 w-3.5" />}>
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Package className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Total</p>
            <p className="text-lg font-semibold text-text-primary">{prescriptions.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
            <CheckCircle className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Ready to Dispense</p>
            <p className="text-lg font-semibold text-text-primary">{verified}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-violet-50 flex items-center justify-center">
            <Package className="h-5 w-5 text-violet-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Dispensed</p>
            <p className="text-lg font-semibold text-text-primary">{dispensed}</p>
          </div>
        </div>
      </div>

      <Card padding={false}>
        {loading ? (
          <div className="p-6"><TableSkeleton rows={5} cols={5} /></div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <p className="text-sm font-medium text-text-primary">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchData} className="mt-3">Try again</Button>
          </div>
        ) : (
          <DataTable
            data={prescriptions}
            keyExtractor={(rx) => rx.id}
            emptyMessage="No prescriptions available for dispensing."
            emptyIcon={<Inbox className="h-12 w-12" />}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (rx) => <span className="font-mono text-xs text-text-secondary">{rx.id.slice(0, 12)}...</span>,
              },
              {
                key: "status",
                header: "Status",
                render: (rx) => <StatusBadge status={rx.status} />,
              },
              {
                key: "dispensing",
                header: "Dispensing",
                render: (rx) => rx.dispensing_status
                  ? <StatusBadge status={rx.dispensing_status} />
                  : <span className="text-text-tertiary text-xs">--</span>,
              },
              {
                key: "date",
                header: "Date",
                render: (rx) => (
                  <span className="text-text-secondary text-xs">
                    {new Date(rx.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                render: (rx) => (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleDownload(rx.id)}
                      loading={actionLoading === rx.id + "-dl"}
                      icon={<Download className="h-3.5 w-3.5" />}
                    >
                      PDF
                    </Button>
                    {(rx.status === "verified" || rx.status === "available") && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleDispense(rx.id)}
                        loading={actionLoading === rx.id + "-disp"}
                        icon={<CheckCircle className="h-3.5 w-3.5" />}
                      >
                        Dispense
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
