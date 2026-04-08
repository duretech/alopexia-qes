"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import QRCode from "react-qr-code";
import type { PortalKind } from "../lib/session";
import { setSession, type SessionUser } from "../lib/session";
import { Button } from "./Button";
import { TextField } from "./TextField";

type LoginState =
  | { step: "credentials" }
  | { step: "mfa"; mfa_token: string }
  | { step: "enroll"; enrollment_token: string; otpauth_uri: string };

export function LoginView({
  portal,
  heroTitle,
  heroSubtitle,
}: {
  portal: PortalKind;
  heroTitle: string;
  heroSubtitle: string;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [state, setState] = useState<LoginState>({ step: "credentials" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, portal }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Login failed");
        return;
      }
      if (data.status === "authenticated") {
        persistAndGo(data.token, data.user);
        return;
      }
      if (data.status === "mfa_required") {
        setState({ step: "mfa", mfa_token: data.mfa_token });
        return;
      }
      if (data.status === "mfa_enrollment") {
        setState({
          step: "enroll",
          enrollment_token: data.enrollment_token,
          otpauth_uri: data.otpauth_uri,
        });
        return;
      }
      setError("Unexpected response");
    } catch {
      setError("Network error — is the API running?");
    } finally {
      setLoading(false);
    }
  }

  async function submitMfa(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/mfa/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mfa_token: state.step === "mfa" ? state.mfa_token : "",
          code: code.replace(/\s/g, ""),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Verification failed");
        return;
      }
      persistAndGo(data.token, data.user);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  async function submitEnroll(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/mfa/complete-enrollment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enrollment_token: state.step === "enroll" ? state.enrollment_token : "",
          code: code.replace(/\s/g, ""),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Enrollment failed");
        return;
      }
      persistAndGo(data.token, data.user);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  function persistAndGo(token: string, user: Record<string, unknown>) {
    const normalized: SessionUser = {
      id: String(user.id),
      email: String(user.email),
      full_name: String(user.full_name ?? ""),
      role: String(user.role),
      tenant_id: String(user.tenant_id),
    };
    setSession(portal, { token, user: normalized });
    router.replace("/");
    router.refresh();
  }

  return (
    <div className="qes-login-page" data-portal={portal}>
      <div className="qes-login-hero">
        <h1>{heroTitle}</h1>
        <p>{heroSubtitle}</p>
      </div>
      <div className="qes-login-panel">
        <div className="qes-login-card">
          {state.step === "credentials" && (
            <>
              <h2>Sign in</h2>
              <p className="qes-login-card__sub">Use your work email. Multi-factor authentication is required.</p>
              <form onSubmit={submitCredentials} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="Email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@organization.com"
                />
                <TextField
                  label="Password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  hint="Mock mode: any password is accepted."
                />
                {error && (
                  <div className="qes-alert qes-alert--error" role="alert">
                    {error}
                  </div>
                )}
                <Button variant="primary" type="submit" disabled={loading} style={{ width: "100%" }}>
                  {loading ? "Signing in…" : "Continue"}
                </Button>
              </form>
            </>
          )}

          {state.step === "mfa" && (
            <>
              <h2>Authenticator code</h2>
              <p className="qes-login-card__sub">Enter the 6-digit code from your authenticator app.</p>
              <form onSubmit={submitMfa} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="One-time code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={8}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                  placeholder="000000"
                />
                {error && (
                  <div className="qes-alert qes-alert--error" role="alert">
                    {error}
                  </div>
                )}
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setState({ step: "credentials" });
                      setCode("");
                      setError(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button variant="primary" type="submit" disabled={loading} style={{ flex: 1 }}>
                    {loading ? "Verifying…" : "Verify"}
                  </Button>
                </div>
              </form>
            </>
          )}

          {state.step === "enroll" && (
            <>
              <h2>Set up authenticator</h2>
              <p className="qes-login-card__sub">
                Scan the QR code with Google Authenticator, 1Password, or another TOTP app, then enter the code to
                finish enrollment.
              </p>
              <div className="qes-qr">
                <QRCode value={state.otpauth_uri} size={180} style={{ height: "auto", maxWidth: "100%" }} />
              </div>
              <form onSubmit={submitEnroll} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="Confirm code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={8}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
                {error && (
                  <div className="qes-alert qes-alert--error" role="alert">
                    {error}
                  </div>
                )}
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setState({ step: "credentials" });
                      setCode("");
                      setError(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button variant="primary" type="submit" disabled={loading} style={{ flex: 1 }}>
                    {loading ? "Saving…" : "Complete setup"}
                  </Button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
