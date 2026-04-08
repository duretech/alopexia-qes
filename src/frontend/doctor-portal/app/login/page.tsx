"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Shield, Lock, Mail, ArrowRight, KeyRound } from "lucide-react";

export default function LoginPage() {
  const { login, verifyMfa } = useAuth();
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mfaRefs = useRef<(HTMLInputElement | null)[]>([]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await login(email, password);
      if (result.requiresMfa) {
        setStep("mfa");
      } else {
        window.location.href = "/";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleMfa() {
    const code = mfaCode.join("");
    if (code.length !== 6) return;
    setLoading(true);
    setError(null);
    try {
      await verifyMfa(code);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
      setMfaCode(["", "", "", "", "", ""]);
      mfaRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  }

  function handleMfaInput(index: number, value: string) {
    if (!/^\d*$/.test(value)) return;
    const next = [...mfaCode];
    next[index] = value.slice(-1);
    setMfaCode(next);
    if (value && index < 5) mfaRefs.current[index + 1]?.focus();
  }

  function handleMfaKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !mfaCode[index] && index > 0) {
      mfaRefs.current[index - 1]?.focus();
    }
  }

  useEffect(() => {
    if (mfaCode.every((d) => d !== "")) handleMfa();
  }, [mfaCode]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-950 via-primary-900 to-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-primary-500/20 backdrop-blur-sm border border-primary-400/30 mb-4">
            <Shield className="h-7 w-7 text-primary-300" />
          </div>
          <h1 className="text-2xl font-bold text-white">QES Flow</h1>
          <p className="text-primary-300 text-sm mt-1">Doctor Portal</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {step === "credentials" ? (
            <>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-text-primary">Welcome back</h2>
                <p className="text-sm text-text-secondary mt-1">Sign in to manage prescriptions</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <Input
                  label="Email address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="doctor@clinic.com"
                  required
                  autoFocus
                />

                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />

                {error && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200">
                    <div className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <Button type="submit" loading={loading} className="w-full" size="lg" icon={<ArrowRight className="h-4 w-4" />}>
                  Sign in
                </Button>
              </form>

              <div className="mt-6 pt-6 border-t border-border">
                <p className="text-xs text-text-tertiary text-center">
                  Protected by QES Flow. All sessions are monitored and audited.
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-primary-50 mb-3">
                  <KeyRound className="h-6 w-6 text-primary-600" />
                </div>
                <h2 className="text-lg font-semibold text-text-primary">Two-factor authentication</h2>
                <p className="text-sm text-text-secondary mt-1">
                  Enter the 6-digit code from your authenticator app
                </p>
              </div>

              <div className="flex justify-center gap-2 mb-6">
                {mfaCode.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => { mfaRefs.current[i] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleMfaInput(i, e.target.value)}
                    onKeyDown={(e) => handleMfaKeyDown(i, e)}
                    className="w-11 h-13 text-center text-xl font-semibold rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-colors"
                    autoFocus={i === 0}
                  />
                ))}
              </div>

              {error && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200 mb-4">
                  <div className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <Button loading={loading} onClick={handleMfa} className="w-full" size="lg">
                Verify
              </Button>

              <button
                onClick={() => { setStep("credentials"); setError(null); }}
                className="mt-4 w-full text-sm text-text-secondary hover:text-text-primary text-center cursor-pointer"
              >
                Back to sign in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
