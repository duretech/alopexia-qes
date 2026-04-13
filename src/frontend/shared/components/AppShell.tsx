"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import type { PortalKind, SessionUser } from "../lib/session";
import { Button } from "./Button";

export type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
};

type AppShellProps = {
  portal: PortalKind;
  portalLabel: string;
  navItems: NavItem[];
  user: SessionUser;
  onLogout: () => void;
  children: ReactNode;
};

export function AppShell(props: AppShellProps) {
  const { portal, portalLabel, navItems, user, onLogout, children } = props;
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="qes-shell" data-portal={portal}>
      {/* <button
        type="button"
        className={`qes-sidebar-overlay ${menuOpen ? "qes-sidebar-overlay--show" : ""}`}
        aria-label="Close menu"
        onClick={() => setMenuOpen(false)}
      /> */}
      <aside className={`qes-sidebar ${menuOpen ? "qes-sidebar--open" : ""}`}>
        <div className="qes-sidebar__brand">
          <p className="qes-sidebar__logo">QES Flow</p>
          <h1 className="qes-sidebar__title">{portalLabel}</h1>
        </div>
        <nav className="qes-sidebar__nav" aria-label="Main">
          {navItems.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`qes-nav-item ${active ? "qes-nav-item--active" : ""}`}
                onClick={() => setMenuOpen(false)}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="qes-sidebar__foot">© QES Flow</div>
      </aside>
      <div className="qes-main">
        <header className="qes-topbar">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Button variant="ghost" className="qes-menu-toggle" onClick={() => setMenuOpen(true)} aria-label="Open menu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </Button>
            <h2 className="qes-topbar__title">{portalLabel}</h2>
          </div>
          <div className="qes-topbar__actions">
            <span className="qes-user-chip" title={user.phone_number}>
              {user.full_name || user.phone_number}
            </span>
            <Button variant="secondary" onClick={onLogout}>
              Sign out
            </Button>
          </div>
        </header>
        <div className="qes-content">{children}</div>
      </div>
    </div>
  );
}
