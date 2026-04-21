import { LoginView } from "@qes-ui/components/LoginView";

export default function LoginPage() {
  return (
    <LoginView
      portal="admin"
      logoSrc="/admin/logo.png"
      heroTitle="Compliance without compromise"
      heroSubtitle="Export immutable audit trails, manage legal holds, and run controlled deletion workflows with dual approval."
    />
  );
}
