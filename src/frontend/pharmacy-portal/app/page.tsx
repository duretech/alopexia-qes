"use client";

import { useEffect, useState } from "react";

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

  useEffect(() => {
    fetch("/api/v1/pharmacy/prescriptions")
      .then((res) => (res.ok ? res.json() : []))
      .then(setPrescriptions)
      .catch(() => setPrescriptions([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleDownload(prescriptionId: string) {
    try {
      const res = await fetch(
        `/api/v1/pharmacy/prescriptions/${prescriptionId}/download`
      );
      if (res.ok) {
        const data = await res.json();
        window.open(data.signed_url, "_blank");
      } else {
        alert("Failed to generate download URL");
      }
    } catch {
      alert("Network error");
    }
  }

  async function handleDispense(prescriptionId: string) {
    if (!confirm("Confirm dispensing of this prescription?")) return;

    try {
      const res = await fetch(
        `/api/v1/pharmacy/prescriptions/${prescriptionId}/dispense`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ dispensing_status: "dispensed" }),
        }
      );
      if (res.ok) {
        setPrescriptions((prev) =>
          prev.map((rx) =>
            rx.id === prescriptionId
              ? { ...rx, status: "dispensed", dispensing_status: "dispensed" }
              : rx
          )
        );
      } else {
        const err = await res.json();
        alert(err.detail || "Dispensing failed");
      }
    } catch {
      alert("Network error");
    }
  }

  if (loading) return <p>Loading prescriptions...</p>;

  return (
    <div>
      <h2>Prescriptions</h2>
      <p style={{ color: "#666" }}>
        View verified prescriptions, download PDFs, and confirm dispensing.
      </p>

      {prescriptions.length === 0 ? (
        <p>No prescriptions available.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>ID</th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>Status</th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>
                Dispensing
              </th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>
                Created
              </th>
              <th style={{ textAlign: "left", padding: "0.75rem" }}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {prescriptions.map((rx) => (
              <tr key={rx.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td
                  style={{
                    padding: "0.75rem",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                  }}
                >
                  {rx.id.slice(0, 8)}...
                </td>
                <td style={{ padding: "0.75rem" }}>{rx.status}</td>
                <td style={{ padding: "0.75rem" }}>
                  {rx.dispensing_status || "—"}
                </td>
                <td style={{ padding: "0.75rem" }}>
                  {new Date(rx.created_at).toLocaleDateString("es-ES")}
                </td>
                <td style={{ padding: "0.75rem", display: "flex", gap: "0.5rem" }}>
                  <button
                    onClick={() => handleDownload(rx.id)}
                    style={{
                      padding: "0.25rem 0.75rem",
                      background: "#4299e1",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    Download PDF
                  </button>
                  {(rx.status === "verified" || rx.status === "available") && (
                    <button
                      onClick={() => handleDispense(rx.id)}
                      style={{
                        padding: "0.25rem 0.75rem",
                        background: "#48bb78",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                    >
                      Dispense
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
