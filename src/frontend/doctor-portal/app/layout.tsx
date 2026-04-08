import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/toast";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "QES Flow — Doctor Portal",
  description: "Prescription upload and management for doctors",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <AuthProvider>
          <ToastProvider>
            <Sidebar />
            <main className="lg:pl-64 pt-14 lg:pt-0 min-h-screen">
              <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {children}
              </div>
            </main>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
