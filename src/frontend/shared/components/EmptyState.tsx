import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="qes-empty">
      <h3 className="qes-empty__title">{title}</h3>
      {description && <p className="qes-empty__desc">{description}</p>}
      {action && <div className="qes-empty__action">{action}</div>}
    </div>
  );
}
