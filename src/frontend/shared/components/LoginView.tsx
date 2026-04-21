"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { PortalKind } from "../lib/session";
import { setSession, type SessionUser } from "../lib/session";
import { Button } from "./Button";
import { TextField } from "./TextField";

type LoginState =
  | { step: "phone" }
  | { step: "otp"; otp_token: string }
  | { step: "pin"; pin_token: string };

export function LoginView({
  portal,
  heroTitle,
  heroSubtitle,
  logoSrc = "/logo.png",
}: {
  portal: PortalKind;
  heroTitle: string;
  heroSubtitle: string;
  logoSrc?: string;
}) {
  const router = useRouter();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [code, setCode] = useState("");
  const [state, setState] = useState<LoginState>({ step: "phone" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitPhone(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phoneNumber, portal }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Login failed");
        return;
      }
      if (data.status === "otp_required") {
        setState({ step: "otp", otp_token: data.otp_token });
        if (data.otp_debug) {
          setError(`Test OTP: ${data.otp_debug}`);
        }
        return;
      }
      setError("Unexpected response");
    } catch {
      setError("Network error — is the API running?");
    } finally {
      setLoading(false);
    }
  }

  async function submitOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          otp_token: state.step === "otp" ? state.otp_token : "",
          otp_code: code.replace(/\s/g, ""),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Verification failed");
        return;
      }
      if (data.status === "pin_required") {
        setState({ step: "pin", pin_token: data.pin_token });
        setCode("");
        return;
      }
      setError("Unexpected response");
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  async function submitPin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/pin/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pin_token: state.step === "pin" ? state.pin_token : "",
          pin: code.replace(/\s/g, ""),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "PIN verification failed");
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
      phone_number: String(user.phone_number),
      full_name: String(user.full_name ?? ""),
      role: String(user.role),
      tenant_id: String(user.tenant_id),
      clinic_id: user.clinic_id ? String(user.clinic_id) : undefined,
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
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={logoSrc} alt="Centa Bio Lab" style={{ height: "48px", width: "auto", marginBottom: "1rem" }} />
          {state.step === "phone" && (
            <>
              <h2>Sign in with phone</h2>
              <p className="qes-login-card__sub">Enter your phone number to receive a one-time OTP.</p>
              <form onSubmit={submitPhone} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="Phone number"
                  type="tel"
                  autoComplete="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  required
                  placeholder="+34XXXXXXXXX"
                />
                {error && (
                  <div className="qes-alert qes-alert--error" role="alert">
                    {error}
                  </div>
                )}
                <Button variant="primary" type="submit" disabled={loading} style={{ width: "100%" }}>
                  {loading ? "Sending OTP…" : "Continue"}
                </Button>
              </form>
            </>
          )}

          {state.step === "otp" && (
            <>
              <h2>Enter OTP</h2>
              <p className="qes-login-card__sub">Enter the code sent to your phone.</p>
              <form onSubmit={submitOtp} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="OTP code"
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
                      setState({ step: "phone" });
                      setCode("");
                      setError(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button variant="primary" type="submit" disabled={loading} style={{ flex: 1 }}>
                    {loading ? "Verifying OTP…" : "Verify OTP"}
                  </Button>
                </div>
              </form>
            </>
          )}

          {state.step === "pin" && (
            <>
              <h2>Multi-factor PIN</h2>
              <p className="qes-login-card__sub">Enter your secure PIN to complete MFA.</p>
              <form onSubmit={submitPin} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <TextField
                  label="PIN"
                  type="password"
                  inputMode="numeric"
                  autoComplete="off"
                  pattern="[0-9]*"
                  maxLength={12}
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
                      setState({ step: "phone" });
                      setCode("");
                      setError(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button variant="primary" type="submit" disabled={loading} style={{ flex: 1 }}>
                    {loading ? "Verifying PIN…" : "Verify PIN"}
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
