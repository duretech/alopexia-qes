type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "purple";

const variants: Record<BadgeVariant, string> = {
  default: "bg-slate-100 text-slate-700",
  success: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
  warning: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20",
  danger: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20",
  info: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20",
  purple: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  dot?: boolean;
}

export function Badge({ children, variant = "default", dot }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium ${variants[variant]}`}>
      {dot && (
        <span className={`h-1.5 w-1.5 rounded-full ${
          variant === "success" ? "bg-emerald-500" :
          variant === "warning" ? "bg-amber-500" :
          variant === "danger" ? "bg-red-500" :
          variant === "info" ? "bg-blue-500" :
          variant === "purple" ? "bg-violet-500" :
          "bg-slate-500"
        }`} />
      )}
      {children}
    </span>
  );
}

const statusMap: Record<string, { label: string; variant: BadgeVariant }> = {
  pending_verification: { label: "Pending", variant: "warning" },
  verified: { label: "Verified", variant: "success" },
  available: { label: "Available", variant: "info" },
  dispensed: { label: "Dispensed", variant: "purple" },
  failed_verification: { label: "Failed", variant: "danger" },
  expired: { label: "Expired", variant: "default" },
  revoked: { label: "Revoked", variant: "danger" },
};

export function StatusBadge({ status }: { status: string }) {
  const config = statusMap[status] || { label: status.replace(/_/g, " "), variant: "default" as BadgeVariant };
  return <Badge variant={config.variant} dot>{config.label}</Badge>;
}
