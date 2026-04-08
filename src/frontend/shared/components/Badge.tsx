import type { ReactNode } from "react";

const toneMap: Record<string, string> = {
  default: "qes-badge",
  success: "qes-badge qes-badge--success",
  warning: "qes-badge qes-badge--warning",
  danger: "qes-badge qes-badge--danger",
  neutral: "qes-badge qes-badge--neutral",
};

export function Badge({
  tone = "default",
  children,
}: {
  tone?: keyof typeof toneMap;
  children: ReactNode;
}) {
  return <span className={toneMap[tone]}>{children}</span>;
}
