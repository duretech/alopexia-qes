import { AuthGate } from "@qes-ui/components/AuthGate";
import { DoctorShell } from "../components/DoctorShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate portal="clinic">
      <DoctorShell>{children}</DoctorShell>
    </AuthGate>
  );
}
