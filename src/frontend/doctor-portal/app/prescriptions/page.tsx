"use client";

import { useEffect, useState } from "react";

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

  useEffect(() => {
    fetch("/api/v1/pharmacy/prescriptions")
      .then((res) => (res.ok ? res.json() : []))
      .then(setPrescriptions)
      .catch(() => setPrescriptions([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading prescriptions...</p>;

  return (
    <div>
      <h2>My Prescriptions</h2>
      {prescriptions.length === 0 ? (
        <p style={{ color: "#666" }}>No prescriptions found.</p>
      ) : (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            marginTop: "1rem",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>ID</th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>Status</th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>
                Verification
              </th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>
                Created
              </th>
            </tr>
          </thead>
          <tbody>
            {prescriptions.map((rx) => (
              <tr
                key={rx.id}
                style={{ borderBottom: "1px solid #e2e8f0" }}
              >
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontSize: "0.85rem" }}>
                  {rx.id.slice(0, 8)}...
                </td>
                <td style={{ padding: "0.75rem" }}>
                  <StatusBadge status={rx.status} />
                </td>
                <td style={{ padding: "0.75rem" }}>
                  {rx.verification_status || "—"}
                </td>
                <td style={{ padding: "0.75rem" }}>
                  {new Date(rx.created_at).toLocaleDateString("es-ES")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending_verification: "#ecc94b",
    verified: "#48bb78",
    available: "#4299e1",
    dispensed: "#9f7aea",
    failed_verification: "#fc8181",
  };
  return (
    <span
      style={{
        padding: "0.25rem 0.5rem",
        borderRadius: "4px",
        background: colors[status] || "#e2e8f0",
        color: colors[status] ? "white" : "black",
        fontSize: "0.85rem",
      }}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
