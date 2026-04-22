import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QTSP Flow — Pharmacy Portal",
  description: "Verified prescriptions and dispensing workflow",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" data-portal="pharmacy">
      <body>{children}</body>
    </html>
  );
}
