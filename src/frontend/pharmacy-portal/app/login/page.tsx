import { LoginView } from "@qes-ui/components/LoginView";

export default function LoginPage() {
  return (
    <LoginView
      portal="pharmacy"
      logoSrc="/pharmacy/logo.png"
      heroTitle="Dispense with confidence"
      heroSubtitle="Access verified electronic prescriptions, review evidence, and record dispensing with a clear audit trail."
    />
  );
}
