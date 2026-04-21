import { LoginView } from "@qes-ui/components/LoginView";

export default function LoginPage() {
  return (
    <LoginView
      portal="clinic"
      logoSrc="/clinic/logo.png"
      heroTitle="Clinic prescription upload portal"
      heroSubtitle="Upload signed PDFs directly from your clinic, track verification status, and maintain a complete audit trail."
    />
  );
}
