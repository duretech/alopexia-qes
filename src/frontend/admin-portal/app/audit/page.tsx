"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { Download, FileText, Calendar } from "lucide-react";

export default function AuditExportPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [exporting, setExporting] = useState(false);
  const { toast } = useToast();

  async function handleExport() {
    setExporting(true);
    try {
      const res = await fetch("/api/v1/admin/audit/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_date: startDate || null,
          end_date: endDate || null,
        }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_export_${new Date().toISOString().slice(0, 10)}.jsonl`;
        a.click();
        URL.revokeObjectURL(url);
        toast("success", "Audit export downloaded successfully");
      } else {
        toast("error", "Export failed — check permissions");
      }
    } catch {
      toast("error", "Network error");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Audit Export</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Export the immutable audit trail for external compliance tools and inspections.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Export Configuration</CardTitle>
          <CardDescription>
            Select a date range to filter audit events. Leave empty to export all events.
          </CardDescription>
        </CardHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <Input
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <Input
            label="End Date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-border">
          <div className="flex items-center gap-2 text-text-tertiary">
            <FileText className="h-4 w-4" />
            <span className="text-xs">Output format: JSON Lines (.jsonl)</span>
          </div>
          <Button
            onClick={handleExport}
            loading={exporting}
            icon={<Download className="h-4 w-4" />}
          >
            Export
          </Button>
        </div>
      </Card>

      {/* Info card */}
      <div className="bg-surface rounded-xl border border-border p-6">
        <h3 className="text-sm font-semibold text-text-primary mb-3">About the Audit Trail</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 mt-0.5">
              <Calendar className="h-4 w-4 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Immutable</p>
              <p className="text-xs text-text-secondary">Hash-chained entries cannot be modified or deleted</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 mt-0.5">
              <FileText className="h-4 w-4 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Complete</p>
              <p className="text-xs text-text-secondary">Every action, login, and data access is recorded</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-lg bg-violet-50 flex items-center justify-center shrink-0 mt-0.5">
              <Download className="h-4 w-4 text-violet-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Portable</p>
              <p className="text-xs text-text-secondary">JSONL format compatible with SIEM and audit tools</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
