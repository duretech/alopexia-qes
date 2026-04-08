import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QES Flow — Doctor Portal",
  description: "Prescription upload and management for doctors",
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
            background: "#1a365d",
            color: "white",
            padding: "1rem 2rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "1.25rem" }}>
            QES Flow — Doctor Portal
          </h1>
          <nav style={{ display: "flex", gap: "1.5rem" }}>
            <a href="/" style={{ color: "white", textDecoration: "none" }}>
              Upload
            </a>
            <a
              href="/prescriptions"
              style={{ color: "white", textDecoration: "none" }}
            >
              My Prescriptions
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
