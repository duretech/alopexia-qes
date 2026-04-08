import type { ReactNode } from "react";

export function Card({
  children,
  className,
  padding = "lg",
}: {
  children: ReactNode;
  className?: string;
  padding?: "none" | "md" | "lg";
}) {
  const p = padding === "none" ? "" : padding === "md" ? "qes-card--pad-md" : "qes-card--pad-lg";
  const extra = className ? ` ${className}` : "";
  return <div className={`qes-card ${p}${extra}`.trim()}>{children}</div>;
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="qes-card__header">
      <div>
        <h2 className="qes-card__title">{title}</h2>
        {description && <p className="qes-card__desc">{description}</p>}
      </div>
      {action && <div className="qes-card__action">{action}</div>}
    </div>
  );
}
