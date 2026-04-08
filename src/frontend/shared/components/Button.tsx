"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variantClass: Record<Variant, string> = {
  primary: "qes-btn qes-btn--primary",
  secondary: "qes-btn qes-btn--secondary",
  ghost: "qes-btn qes-btn--ghost",
  danger: "qes-btn qes-btn--danger",
};

export function Button(
  props: ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: Variant;
    children: ReactNode;
  },
) {
  const { variant = "primary", children, className = "", disabled, type = "button", ...rest } = props;
  return (
    <button
      type={type}
      className={`${variantClass[variant]} ${className}`.trim()}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}
