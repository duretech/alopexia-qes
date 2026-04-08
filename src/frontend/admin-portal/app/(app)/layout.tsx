import { AuthGate } from "@qes-ui/components/AuthGate";
import { AdminShell } from "../components/AdminShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate portal="admin">
      <AdminShell>{children}</AdminShell>
    </AuthGate>
  );
}
