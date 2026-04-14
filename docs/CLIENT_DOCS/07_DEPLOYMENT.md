# Production Deployment Guide

## 🚀 Deployment Overview

QES Flow is designed for production deployment on **Azure Container Instances** with **Docker containerization**. This guide covers deploying to a production environment with all security and compliance features enabled.

---

## 📦 Prerequisites

### **Local Development**
- Docker Desktop installed
- Docker Compose
- Git
- Python 3.9+ (for local testing)
- Node.js 18+ (for frontend builds)

### **Production Infrastructure (Azure)**
- Azure Container Registry (ACR) for Docker images
- Azure Container Instances or App Service for running containers
- Azure Database for PostgreSQL (managed)
- Azure Blob Storage for prescription files
- Azure Key Vault for encryption keys
- Azure Virtual Network (VNet) for network isolation
- Azure Application Gateway (optional, for load balancing)

---

## 🐳 Docker Architecture

### **Multi-Stage Build Process**

```dockerfile
Stage 1: Build Backend
├─ Base: python:3.9-slim
├─ Install dependencies (poetry)
├─ Install Python packages
└─ Compile/optimize code

Stage 2: Build Frontend (Doctor Portal)
├─ Base: node:18-alpine
├─ Install npm dependencies
├─ Build React app
└─ Output static files

Stage 3: Build Frontend (Pharmacy Portal)
├─ Base: node:18-alpine
├─ Install npm dependencies
├─ Build React app
└─ Output static files

Stage 4: Build Frontend (Admin Portal)
├─ Base: node:18-alpine
├─ Install npm dependencies
├─ Build React app
└─ Output static files

Stage 5: Production Runtime
├─ Base: python:3.9-slim
├─ Copy dependencies from Stage 1
├─ Copy frontend builds from Stages 2-4
├─ Nginx to serve static files
├─ FastAPI to run API
└─ Total size: ~500MB
```

### **Why Multi-Stage Build?**

```
Without Multi-Stage (Bad):
├─ Image includes: node, npm, build tools, source code
├─ Size: 2GB+
├─ Startup: Slow (many unnecessary files)
├─ Security: More attack surface

With Multi-Stage (Good):
├─ Image includes: only runtime dependencies
├─ Size: ~500MB
├─ Startup: Fast (only what's needed)
├─ Security: Smaller attack surface
└─ Benefit: 4x smaller, faster deployment, more secure
```

---

## 📋 Environment Configuration

### **Development Environment (docker-compose.yml)**

```yaml
Services:
├─ api (FastAPI)
│  ├─ Environment: development
│  ├─ Debug mode: enabled (--reload)
│  ├─ Hot reload: enabled (./src/backend:/app)
│  ├─ Port: 8000
│  └─ No HTTPS (localhost testing)
│
├─ doctor-portal (React)
│  ├─ Port: 3000
│  ├─ Environment: development
│  └─ Hot reload: enabled
│
├─ pharmacy-portal (React)
│  ├─ Port: 3001
│  └─ Hot reload: enabled
│
├─ admin-portal (React)
│  ├─ Port: 3002
│  └─ Hot reload: enabled
│
└─ postgres (PostgreSQL)
   ├─ Port: 5432
   └─ Data persisted in docker volume
```

### **Production Environment (Azure Container Instances)**

```yaml
API Container:
├─ Environment: production
├─ Debug mode: disabled
├─ Reload: disabled (immutable image)
├─ HTTPS: enabled (TLS 1.2+)
├─ Port: 8000 (internal, not exposed)
├─ Health check: /health/deep every 30s
└─ Memory: 1GB, CPU: 1 core

Frontend Containers (Doctor, Pharmacy, Admin):
├─ Environment: production
├─ HTTPS: enabled (via Azure Application Gateway)
├─ Port: 80 (internal, behind gateway)
├─ Static content: served by Nginx
├─ Memory: 512MB, CPU: 0.5 core
└─ Health check: HTTP 200 on /index.html

Database (Managed PostgreSQL):
├─ VNet integration: private endpoint
├─ Public access: disabled
├─ SSL: required (TLS 1.2+)
├─ Encryption at rest: enabled (TDE)
├─ Automated backups: daily
├─ Geo-redundancy: enabled
└─ 30-day backup retention

Blob Storage (Prescription Files):
├─ VNet integration: private endpoint
├─ Public access: disabled
├─ Encryption: AES-256 (server-side)
├─ Versioning: enabled
├─ Soft delete: enabled (30-day recovery)
└─ Geo-redundancy: enabled
```

---

## 🔑 Secrets Management (Azure Key Vault)

### **What Goes in Key Vault**

**Never** hardcode these in code or config files:

```
Encryption Keys
├─ DATABASE_ENCRYPTION_KEY (rotated every 90 days)
├─ FIELD_ENCRYPTION_KEY (rotated every 90 days)
└─ JWT_SECRET_KEY (for signing tokens)

Database Credentials
├─ DATABASE_URL (connection string)
├─ DATABASE_USER
└─ DATABASE_PASSWORD

API Keys
├─ QTSP_API_KEY (Dokobit)
├─ CLAMAV_API_KEY (if remote scanning)
└─ AZURE_STORAGE_KEY

OAuth / External Services
├─ TWILIO_AUTH_TOKEN (SMS provider)
├─ SENDGRID_API_KEY (email provider)
└─ SLACK_WEBHOOK (alerts)

Certificates
├─ TLS_CERTIFICATE.pem
├─ TLS_PRIVATE_KEY.pem
└─ CA_BUNDLE.pem
```

### **Key Vault Access Control**

```
Application Identity
├─ Service Principal or Managed Identity
├─ RBAC: Key Vault Secrets User
└─ Audit logging: all access logged

Administrative Access
├─ Admin user: Key Vault Administrator role
├─ Requires MFA
└─ Limited to specific time windows
```

---

## 🚢 Deployment Process

### **Step 1: Build Docker Images**

```bash
# Login to Azure Container Registry
az acr login --name myacr

# Build and push API image
docker build -t myacr.azurecr.io/qes-api:latest -f Dockerfile.api .
docker push myacr.azurecr.io/qes-api:latest

# Build and push frontend images
docker build -t myacr.azurecr.io/qes-doctor-portal:latest -f Dockerfile.doctor-portal .
docker push myacr.azurecr.io/qes-doctor-portal:latest

docker build -t myacr.azurecr.io/qes-pharmacy-portal:latest -f Dockerfile.pharmacy-portal .
docker push myacr.azurecr.io/qes-pharmacy-portal:latest

docker build -t myacr.azurecr.io/qes-admin-portal:latest -f Dockerfile.admin-portal .
docker push myacr.azurecr.io/qes-admin-portal:latest
```

### **Step 2: Deploy to Azure Container Instances**

```bash
# Create container group with multiple containers
az container create \
  --resource-group myresourcegroup \
  --name qes-production \
  --image myacr.azurecr.io/qes-api:latest \
  --registry-login-server myacr.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --cpu 1 \
  --memory 1 \
  --port 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    DATABASE_URL="$(az keyvault secret show --vault-name mykeyvault --name database-url --query value -o tsv)" \
    ENCRYPTION_KEY="$(az keyvault secret show --vault-name mykeyvault --name encryption-key --query value -o tsv)" \
  --secure-environment-variables \
    JWT_SECRET="$(az keyvault secret show --vault-name mykeyvault --name jwt-secret --query value -o tsv)"
```

### **Step 3: Configure Azure Application Gateway**

```
Function: Load balancing and HTTPS termination

Configuration:
├─ Frontend IP: Public IP with DDoS protection
├─ Backend Pool:
│  ├─ Doctor Portal container (3000)
│  ├─ Pharmacy Portal container (3001)
│  ├─ Admin Portal container (3002)
│  └─ API container (8000)
├─ HTTP Settings:
│  ├─ Protocol: HTTP (internal, encrypted via VNet)
│  ├─ Port: 8000 for API, 3000/3001/3002 for frontends
│  └─ Health probes: /health every 30s
├─ Listener:
│  ├─ Protocol: HTTPS
│  ├─ Port: 443
│  ├─ Certificate: TLS cert from Key Vault
│  └─ Redirect HTTP → HTTPS
└─ Rules: Route requests to appropriate backend
```

---

## 🔒 Security Configuration

### **Network Security**

```
Azure Virtual Network (VNet)
├─ Private IP range: 10.0.0.0/16
├─ Subnet 1 (API): 10.0.1.0/24
│  ├─ Containers: FastAPI, Nginx
│  └─ NSG rules: Allow 8000 from load balancer only
├─ Subnet 2 (Database): 10.0.2.0/24
│  ├─ Resource: PostgreSQL
│  └─ NSG rules: Allow 5432 from API subnet only
└─ Subnet 3 (Storage): 10.0.3.0/24
   ├─ Resource: Blob Storage (private endpoint)
   └─ NSG rules: Allow from API subnet only
```

### **TLS Configuration**

```
Certificate Management
├─ Source: Azure Key Vault (store .pem files)
├─ Provider: Let's Encrypt (auto-renewal via Azure)
├─ Application Gateway:
│  ├─ Listens on 443 (HTTPS)
│  ├─ Terminates TLS
│  └─ Routes HTTP internally
└─ Internal (Database, Storage):
   ├─ All connections encrypted
   ├─ Certificate verification: enabled
   └─ Min version: TLS 1.2
```

### **Firewall & DDoS**

```
Azure WAF (Web Application Firewall)
├─ Attached to: Application Gateway
├─ Rules:
│  ├─ SQL injection detection
│  ├─ Cross-site scripting (XSS) detection
│  ├─ DDoS protection (Azure DDoS Standard)
│  └─ Geo-blocking (optional)
└─ Logging: all requests logged to Azure Monitor

Rate Limiting (Application Level)
├─ API: 100 req/min per IP
├─ Login: 10 req/min per IP
├─ Upload: 20 req/min per IP
└─ Enforced by FastAPI middleware
```

---

## 📊 Monitoring & Logging

### **Azure Monitor Integration**

```
Container Logs
├─ Destination: Azure Monitor (Log Analytics)
├─ Collection: All stdout/stderr
├─ Retention: 30 days (configurable)
└─ Searchable: Full-text search available

Application Logs
├─ Format: JSON structured logs
├─ Automatic masking: sensitive data masked
├─ Fields: timestamp, level, message, context
└─ Integration: CloudWatch / Azure Monitor

Metrics
├─ CPU usage
├─ Memory usage
├─ Request latency (p50, p99)
├─ Error rate
├─ Database connections
└─ Storage access patterns
```

### **Alerts**

```
Critical Alerts (Page on-call immediately)
├─ API container down (health check fails)
├─ Database down (connection fails)
├─ High error rate (>1% errors)
└─ Audit log integrity check failed

Warning Alerts (Email to ops team)
├─ CPU usage >80%
├─ Memory usage >85%
├─ Storage quota >90%
└─ Slow API responses (P99 > 5s)

Info Alerts (Dashboard only)
├─ Daily usage statistics
├─ Backup completion status
└─ Certificate expiration (30 days before)
```

---

## 🔄 Scaling & Load Balancing

### **Horizontal Scaling (Multiple Containers)**

```
Production Setup
├─ API Instances: 3 (load balanced)
│  ├─ Instance 1: 10.0.1.10:8000
│  ├─ Instance 2: 10.0.1.11:8000
│  └─ Instance 3: 10.0.1.12:8000
├─ Frontend Instances: 2 each (doctor, pharmacy, admin)
└─ Load Balancer: distributes traffic

Benefits
├─ High availability: if one container fails, others handle traffic
├─ Scalability: add more containers for higher load
├─ Zero-downtime updates: update one instance at a time
└─ Resilience: load balancer detects unhealthy instances
```

### **Auto-Scaling (if using App Service)**

```
Scaling Rules
├─ Metric: CPU usage
├─ Scale up: when CPU > 70% for 5 minutes
│  └─ Add 1 container
├─ Scale down: when CPU < 30% for 10 minutes
│  └─ Remove 1 container
├─ Min instances: 2 (high availability)
├─ Max instances: 10 (cost control)
└─ Cooldown: 5 minutes between scaling actions
```

---

## 💾 Backup & Disaster Recovery

### **Backup Strategy**

```
Database Backups
├─ Frequency: Automated daily by Azure
├─ Retention: 30 days (configurable up to 35 days)
├─ Redundancy: Geo-redundant (automatic)
├─ Location: Azure backup storage
└─ RTO: 1 hour, RPO: 1 hour

File Backups (Blob Storage)
├─ Replication: Geo-redundant (automatic)
├─ Versioning: All versions retained
├─ Soft delete: 30-day recovery window
└─ Archive: Cold storage after 90 days

Audit Log Backups
├─ Export: Daily JSON Lines export
├─ Location: Azure Archive Storage (Glacier equivalent)
├─ Retention: 7 years (legal requirement)
└─ Encryption: Separate backup encryption key
```

### **Disaster Recovery Process**

```
Detection (Automated)
└─ Health check fails for 2 consecutive checks (1 minute total)

Response (Automated)
├─ Trigger failover
├─ Load balancer removes unhealthy instance
├─ New instance starts from image
├─ Database connection restored
└─ Services resume

Manual Intervention (If Needed)
├─ Restore database from backup
├─ Restore files from blob storage backup
├─ Verify integrity (hash checks)
├─ Run smoke tests
└─ Resume production traffic
```

---

## 🧪 Testing Before Production

### **Pre-Production Checklist**

```
Infrastructure Tests
☐ All containers start successfully
☐ Health checks pass (/health/live, /health/ready, /health/deep)
☐ Database connection works
☐ Blob storage accessible
☐ Key Vault accessible
☐ TLS certificates valid
☐ DNS resolves correctly
☐ Load balancer routing works

Application Tests
☐ Login flow works (OTP → PIN)
☐ Upload prescription works
☐ Download prescription works
☐ QTSP verification works
☐ Malware scanning works
☐ Audit logs created
☐ All 3 portals accessible
☐ RBAC permissions enforced

Security Tests
☐ SQL injection prevented
☐ XSS prevention working
☐ Rate limiting enforced
☐ Unauthorized access blocked
☐ Encryption working
☐ Audit trail immutable
☐ Sensitive data masked in logs
└─ HTTPS enforced (no HTTP)

Compliance Tests
☐ GDPR data export working
☐ Data deletion requests processed
☐ Audit logs exportable
☐ Encryption keys rotated
└─ All documentation up-to-date
```

---

## 📝 Deployment Checklist

Before deploying to production:

- [ ] All services containerized
- [ ] Environment variables in Key Vault (not in code)
- [ ] TLS certificates obtained and stored
- [ ] Azure infrastructure provisioned
- [ ] Network security groups configured
- [ ] Managed Identity created for app authentication
- [ ] Database initialized with schema
- [ ] Blob storage created and encrypted
- [ ] Key Vault provisioned with all secrets
- [ ] Application Gateway configured
- [ ] WAF rules configured
- [ ] Monitoring and alerts configured
- [ ] Backup strategy enabled
- [ ] Disaster recovery tested
- [ ] All security tests passed
- [ ] Compliance requirements verified
- [ ] Documentation reviewed with client
- [ ] Support contacts configured
- [ ] On-call rotation established
- [ ] Post-deployment runbook prepared

---

## Next Steps

For more details, see:
- [OPERATIONS.md](./08_OPERATIONS.md) — Day-to-day operations
- [BACKUP_RECOVERY.md](./09_BACKUP_RECOVERY.md) — Backup and recovery procedures
- [SECURITY.md](./03_SECURITY.md) — Security implementation details
