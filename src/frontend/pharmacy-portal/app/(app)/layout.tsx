import { AuthGate } from "@qes-ui/components/AuthGate";
import { PharmacyShell } from "../components/PharmacyShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate portal="pharmacy">
      <PharmacyShell>{children}</PharmacyShell>
    </AuthGate>
  );
}
