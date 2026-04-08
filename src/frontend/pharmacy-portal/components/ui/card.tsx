interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export function Card({ children, className = "", padding = true }: CardProps) {
  return (
    <div className={`bg-surface rounded-xl border border-border shadow-sm ${padding ? "p-6" : ""} ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`mb-4 ${className}`}>{children}</div>;
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-base font-semibold text-text-primary">{children}</h3>;
}

export function CardDescription({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-sm text-text-secondary">{children}</p>;
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: { value: string; positive: boolean };
  href?: string;
}

export function StatCard({ title, value, icon, trend, href }: StatCardProps) {
  const content = (
    <div className="group bg-surface rounded-xl border border-border shadow-sm p-5 transition-all duration-200 hover:shadow-md hover:border-border-strong">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-text-secondary">{title}</p>
        {icon && <div className="text-text-tertiary">{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-semibold text-text-primary">{value}</p>
      {trend && (
        <p className={`mt-1 text-xs font-medium ${trend.positive ? "text-emerald-600" : "text-red-600"}`}>
          {trend.positive ? "+" : ""}{trend.value}
        </p>
      )}
    </div>
  );
  if (href) return <a href={href} className="block no-underline">{content}</a>;
  return content;
}
