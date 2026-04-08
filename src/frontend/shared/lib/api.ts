import type { PortalKind } from "./session";
import { clearSession, getSession } from "./session";

export type ApiError = {
  error?: string;
  detail?: string | unknown;
  request_id?: string;
};

export async function apiFetch(
  portal: PortalKind,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const session = getSession(portal);
  const headers = new Headers(init.headers);
  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...init, headers });

  if (res.status === 401) {
    clearSession(portal);
  }

  return res;
}

export function formatApiError(data: ApiError): string {
  const d = data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : String(x))).join(
      "; ",
    );
  }
  if (d && typeof d === "object" && "message" in d && typeof (d as { message: string }).message === "string") {
    return (d as { message: string }).message;
  }
  return data.error ?? "Request failed";
}
