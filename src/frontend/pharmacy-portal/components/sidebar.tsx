"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Pill, FileText, LogOut, Menu, X, User } from "lucide-react";

const navItems = [
  { href: "/", label: "Prescriptions", icon: FileText },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";

  const nav = (
    <>
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-primary-600 flex items-center justify-center shrink-0">
            <Pill className="h-5 w-5 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text-primary truncate">QES Flow</p>
            <p className="text-xs text-text-tertiary">Pharmacy Portal</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-0.5">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <a
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                active
                  ? "bg-primary-50 text-primary-700"
                  : "text-text-secondary hover:bg-surface-tertiary hover:text-text-primary"
              }`}
            >
              <item.icon className={`h-4.5 w-4.5 shrink-0 ${active ? "text-primary-600" : ""}`} />
              {item.label}
            </a>
          );
        })}
      </nav>

      {user && (
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
              <User className="h-4 w-4 text-primary-700" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">{user.full_name}</p>
              <p className="text-xs text-text-tertiary truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-1 w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-tertiary hover:text-text-primary transition-colors cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </>
  );

  return (
    <>
      <div className="lg:hidden fixed top-0 inset-x-0 h-14 bg-surface border-b border-border z-30 flex items-center px-4 gap-3">
        <button onClick={() => setMobileOpen(true)} className="text-text-secondary cursor-pointer">
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <Pill className="h-5 w-5 text-primary-600" />
          <span className="font-semibold text-sm">QES Flow</span>
        </div>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 bg-surface flex flex-col shadow-xl">
            <button onClick={() => setMobileOpen(false)} className="absolute top-4 right-4 text-text-tertiary cursor-pointer">
              <X className="h-5 w-5" />
            </button>
            {nav}
          </div>
        </div>
      )}

      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-surface border-r border-border">
        {nav}
      </aside>
    </>
  );
}
