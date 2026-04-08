"use client";

import type { InputHTMLAttributes } from "react";
import { Input } from "./Input";

export function TextField({
  id,
  label,
  hint,
  error,
  className = "",
  ...inputProps
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
}) {
  const eid = id ?? label.replace(/\s+/g, "-").toLowerCase();
  return (
    <div className={`qes-field ${className}`.trim()}>
      <label className="qes-label" htmlFor={eid}>
        {label}
      </label>
      <Input id={eid} aria-invalid={!!error} aria-describedby={error ? `${eid}-err` : hint ? `${eid}-hint` : undefined} {...inputProps} />
      {hint && !error && (
        <p id={`${eid}-hint`} className="qes-hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${eid}-err`} className="qes-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
