"use client";

import { useEffect, useState } from "react";

export default function AdminDashboard() {
  const [health, setHealth] = useState<{ status: string } | null>(null);

  useEffect(() => {
    fetch("/api/v1/../health/live")
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div>
      <h2>Admin Dashboard</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "1.5rem",
          marginTop: "1.5rem",
        }}
      >
        <DashboardCard
          title="API Status"
          value={health ? "Online" : "Offline"}
          color={health ? "#48bb78" : "#fc8181"}
        />
        <DashboardCard title="Audit Export" value="JSON Lines" href="/audit" />
        <DashboardCard
          title="Legal Holds"
          value="Manage"
          href="/legal-holds"
        />
        <DashboardCard
          title="Deletion Requests"
          value="Review"
          href="/deletions"
        />
      </div>

      <section style={{ marginTop: "2rem" }}>
        <h3>Quick Actions</h3>
        <ul style={{ listStyle: "none", padding: 0 }}>
          <li style={{ marginBottom: "0.5rem" }}>
            <a href="/audit">Export audit trail (JSON Lines)</a>
          </li>
          <li style={{ marginBottom: "0.5rem" }}>
            <a href="/legal-holds">Create or release legal holds</a>
          </li>
          <li style={{ marginBottom: "0.5rem" }}>
            <a href="/deletions">Review and approve deletion requests</a>
          </li>
        </ul>
      </section>
    </div>
  );
}

function DashboardCard({
  title,
  value,
  color,
  href,
}: {
  title: string;
  value: string;
  color?: string;
  href?: string;
}) {
  const content = (
    <div
      style={{
        padding: "1.5rem",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        background: "white",
      }}
    >
      <div style={{ fontSize: "0.85rem", color: "#718096" }}>{title}</div>
      <div
        style={{
          fontSize: "1.5rem",
          fontWeight: 600,
          color: color || "#2d3748",
          marginTop: "0.5rem",
        }}
      >
        {value}
      </div>
    </div>
  );

  if (href) {
    return (
      <a href={href} style={{ textDecoration: "none" }}>
        {content}
      </a>
    );
  }
  return content;
}
