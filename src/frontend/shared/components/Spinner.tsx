"use client";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="qes-spinner-wrap" role="status" aria-live="polite">
      <span className="qes-spinner" aria-hidden />
      <span className="qes-spinner__label">{label}</span>
    </span>
  );
}
