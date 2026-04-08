import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QES Flow — Admin Portal",
  description: "Compliance, audit, and administration portal",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif" }}>
        <header
          style={{
            background: "#742a2a",
            color: "white",
            padding: "1rem 2rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "1.25rem" }}>
            QES Flow — Admin Portal
          </h1>
          <nav style={{ display: "flex", gap: "1.5rem" }}>
            <a href="/" style={{ color: "white", textDecoration: "none" }}>
              Dashboard
            </a>
            <a
              href="/audit"
              style={{ color: "white", textDecoration: "none" }}
            >
              Audit
            </a>
            <a
              href="/legal-holds"
              style={{ color: "white", textDecoration: "none" }}
            >
              Legal Holds
            </a>
          </nav>
        </header>
        <main style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
