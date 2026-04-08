"use client";

import { useEffect, useState } from "react";
import { StatCard } from "@/components/ui/card";
import { CardSkeleton } from "@/components/ui/skeleton";
import { Activity, ScrollText, Lock, Trash2, CheckCircle2, AlertTriangle } from "lucide-react";

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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">System overview and compliance quick actions.</p>
      </div>

      {/* Status banner */}
      {!loading && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
          health ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
        }`}>
          {health ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <div>
                <p className="text-sm font-medium text-emerald-800">All systems operational</p>
                <p className="text-xs text-emerald-700">API, database, and queue workers are running normally.</p>
              </div>
            </>
          ) : (
            <>
              <AlertTriangle className="h-5 w-5 text-red-600 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-800">System unreachable</p>
                <p className="text-xs text-red-700">Unable to connect to the API. Check backend status.</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="API Status"
            value={health ? "Online" : "Offline"}
            icon={<Activity className={`h-5 w-5 ${health ? "text-emerald-500" : "text-red-500"}`} />}
          />
          <StatCard
            title="Audit Export"
            value="Export"
            icon={<ScrollText className="h-5 w-5" />}
            href="/audit"
          />
          <StatCard
            title="Legal Holds"
            value="Manage"
            icon={<Lock className="h-5 w-5" />}
            href="/legal-holds"
          />
          <StatCard
            title="Deletion Requests"
            value="Review"
            icon={<Trash2 className="h-5 w-5" />}
            href="/deletions"
          />
        </div>
      )}

      {/* Quick actions */}
      <div className="bg-surface rounded-xl border border-border p-6">
        <h2 className="text-base font-semibold text-text-primary mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <a href="/audit" className="group flex items-center gap-3 px-4 py-3 rounded-lg border border-border hover:border-primary-200 hover:bg-primary-50/50 transition-colors no-underline">
            <div className="h-9 w-9 rounded-lg bg-amber-50 flex items-center justify-center">
              <ScrollText className="h-4.5 w-4.5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Export Audit Trail</p>
              <p className="text-xs text-text-tertiary">JSON Lines format</p>
            </div>
          </a>
          <a href="/legal-holds" className="group flex items-center gap-3 px-4 py-3 rounded-lg border border-border hover:border-primary-200 hover:bg-primary-50/50 transition-colors no-underline">
            <div className="h-9 w-9 rounded-lg bg-blue-50 flex items-center justify-center">
              <Lock className="h-4.5 w-4.5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Manage Legal Holds</p>
              <p className="text-xs text-text-tertiary">Place or release holds</p>
            </div>
          </a>
          <a href="/deletions" className="group flex items-center gap-3 px-4 py-3 rounded-lg border border-border hover:border-primary-200 hover:bg-primary-50/50 transition-colors no-underline">
            <div className="h-9 w-9 rounded-lg bg-red-50 flex items-center justify-center">
              <Trash2 className="h-4.5 w-4.5 text-red-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">Review Deletions</p>
              <p className="text-xs text-text-tertiary">Dual-approval workflow</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}
