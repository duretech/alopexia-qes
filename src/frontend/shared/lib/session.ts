export type PortalKind = "doctor" | "pharmacy" | "admin";

export type SessionUser = {
  id: string;
  phone_number: string;
  full_name: string;
  role: string;
  tenant_id: string;
};

export type StoredSession = {
  token: string;
  user: SessionUser;
};

function key(portal: PortalKind): string {
  return `qesflow.session.${portal}`;
}

export function getSession(portal: PortalKind): StoredSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key(portal));
    if (!raw) return null;
    const data = JSON.parse(raw) as StoredSession;
    if (!data?.token || !data?.user) return null;
    return data;
  } catch {
    return null;
  }
}

export function setSession(portal: PortalKind, session: StoredSession): void {
  localStorage.setItem(key(portal), JSON.stringify(session));
}

export function clearSession(portal: PortalKind): void {
  localStorage.removeItem(key(portal));
}
