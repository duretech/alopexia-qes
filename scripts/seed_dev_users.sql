-- Dev-only seed: tenant, clinic, doctor, pharmacy user, admin (compliance officer).
-- Run after migrations: psql $DATABASE_URL -f scripts/seed_dev_users.sql
-- Emails: doctor@qesflow.local, pharmacy@qesflow.local, admin@qesflow.local

BEGIN;

INSERT INTO alopexiaqes.tenants (id, name, display_name, is_active, settings, is_deleted)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'dev-tenant',
  'Development Tenant',
  TRUE,
  '{}',
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.clinics (id, tenant_id, name, is_active, is_deleted)
VALUES (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'Development Clinic',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.patients (
  id, tenant_id, identifier_hash, full_name_encrypted, is_active, is_deleted
) VALUES (
  '66666666-6666-6666-6666-666666666666',
  '11111111-1111-1111-1111-111111111111',
  repeat('a', 64),
  'ZGV2LXBsYWNlaG9sZGVy',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.doctors (
  id, tenant_id, external_idp_id, email, full_name, clinic_id, is_active, is_deleted
) VALUES (
  '33333333-3333-3333-3333-333333333333',
  '11111111-1111-1111-1111-111111111111',
  'mock:doctor:dev-1',
  'doctor@qesflow.local',
  'Dev Doctor',
  '22222222-2222-2222-2222-222222222222',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.pharmacy_users (
  id, tenant_id, external_idp_id, email, full_name, pharmacy_name, is_active, is_deleted
) VALUES (
  '44444444-4444-4444-4444-444444444444',
  '11111111-1111-1111-1111-111111111111',
  'mock:pharmacy:dev-1',
  'pharmacy@qesflow.local',
  'Dev Pharmacist',
  'Dev Pharmacy',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.admin_users (
  id, tenant_id, external_idp_id, email, full_name, role, is_active, is_deleted
) VALUES (
  '55555555-5555-5555-5555-555555555555',
  '11111111-1111-1111-1111-111111111111',
  'mock:admin:dev-1',
  'admin@qesflow.local',
  'Dev Compliance',
  'compliance_officer',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

COMMIT;
