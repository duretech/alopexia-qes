import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QES Flow — Admin Portal",
  description: "Compliance, audit, and administration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" data-portal="admin">
      <body>{children}</body>
    </html>
  );
}
