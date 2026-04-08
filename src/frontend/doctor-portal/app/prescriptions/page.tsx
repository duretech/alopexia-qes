"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { FileText, RefreshCw, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Prescription {
  id: string;
  status: string;
  verification_status: string | null;
  upload_checksum: string;
  created_at: string;
}

export default function PrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My Prescriptions</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Track the status of your uploaded prescriptions.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={fetchData} icon={<RefreshCw className="h-3.5 w-3.5" />}>
          Refresh
        </Button>
      </div>

      <Card padding={false}>
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={5} cols={4} />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <div className="h-12 w-12 rounded-full bg-red-50 flex items-center justify-center mb-3">
              <FileText className="h-6 w-6 text-red-400" />
            </div>
            <p className="text-sm font-medium text-text-primary">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchData} className="mt-3">
              Try again
            </Button>
          </div>
        ) : (
          <DataTable
            data={prescriptions}
            keyExtractor={(rx) => rx.id}
            emptyMessage="No prescriptions yet. Upload your first prescription to get started."
            emptyIcon={<Inbox className="h-12 w-12" />}
            columns={[
              {
                key: "id",
                header: "Prescription ID",
                render: (rx) => (
                  <span className="font-mono text-xs text-text-secondary">{rx.id.slice(0, 12)}...</span>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (rx) => <StatusBadge status={rx.status} />,
              },
              {
                key: "verification",
                header: "Verification",
                render: (rx) =>
                  rx.verification_status ? (
                    <StatusBadge status={rx.verification_status} />
                  ) : (
                    <span className="text-text-tertiary text-xs">Pending</span>
                  ),
              },
              {
                key: "created_at",
                header: "Uploaded",
                render: (rx) => (
                  <span className="text-text-secondary text-xs">
                    {new Date(rx.created_at).toLocaleDateString("es-ES", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
