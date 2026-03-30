# CLAUDE.md - Odoo ERP (GCP Production)

Odoo 17 ERP running on Google Cloud Platform.

## Project Overview

| Aspect | Details |
|--------|---------|
| GCP Project | `odoo-erp-prod` |
| Region | `asia-northeast1` (Tokyo) |
| Odoo Version | 17.0 |
| GitHub Repo | `emt-jp/odoo` |
| Status | Production on GCP |

## Infrastructure (GCP)

```
Google Cloud Platform (odoo-erp-prod / asia-northeast1)
├── Cloud Run (Odoo application)
│   └── Custom Docker image from Artifact Registry
├── Cloud SQL (PostgreSQL 15, db-custom-2-4096)
│   └── Instance: odoo-db (private IP, VPC peered)
├── Cloud Storage (GCS)
│   └── Bucket: odoo-erp-prod-odoo-filestore (versioned)
├── VPC
│   ├── Network: odoo-vpc (10.0.0.0/24)
│   └── Serverless VPC Connector: odoo-vpc-connector (10.8.0.0/28)
├── Secret Manager
│   ├── odoo-admin-password
│   └── odoo-db-password
├── Artifact Registry
│   └── asia-northeast1-docker.pkg.dev/odoo-erp-prod/odoo
└── Workload Identity Federation
    └── GitHub Actions (emt-jp/odoo) → github-actions-sa
```

## Database Credentials

```
Host: Cloud SQL private IP (via VPC connector)
Instance: odoo-db
Database: odoo
User: odoo
Password: (stored in Secret Manager: odoo-db-password)
```

## Custom Addons

Key custom modules in `addons/`:
- `advanced_analytics` - Business analytics
- `advanced_crm` - CRM enhancements
- `advanced_inventory` - Inventory management
- `advanced_reports` - Custom reporting

## CI/CD

Deployments via GitHub Actions with Workload Identity Federation (no service account keys):
- **Repo**: `emt-jp/odoo`
- **WIF Pool**: `github-pool` → `github-provider`
- **Service Account**: `github-actions-sa` (Cloud Run admin, Artifact Registry writer)

## Commands

### Local Development
```bash
cd /Users/pk/ws/odoo
docker-compose up -d
open http://localhost:8069
```

### GCP Operations
```bash
# Apply infrastructure
cd terraform && terraform apply

# Build and deploy via GitHub Actions
git push origin main

# Check Cloud Run status
gcloud run services describe odoo --region=asia-northeast1 --project=odoo-erp-prod

# View logs
gcloud run services logs read odoo --region=asia-northeast1 --project=odoo-erp-prod

# Connect to Cloud SQL (via proxy)
cloud-sql-proxy odoo-erp-prod:asia-northeast1:odoo-db
```

### Terraform
```bash
cd terraform
terraform plan
terraform apply
```

## Notes

- Cloud Run min-instances=1 (Odoo needs persistent DB connections)
- Workers set to 4 in production config
- Cloud SQL backups daily at 03:00, deletion protection enabled
- Filestore bucket has versioning (keeps 3 versions)
- VPC peering for private Cloud SQL access (no public IP)
