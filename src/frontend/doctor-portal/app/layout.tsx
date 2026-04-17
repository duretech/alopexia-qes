import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QES Flow — Clinic Portal",
  description: "Prescription upload and management for clinics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" data-portal="clinic">
      <body>{children}</body>
    </html>
  );
}
