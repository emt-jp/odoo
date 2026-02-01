# CLAUDE.md - Odoo ERP Migration Project

Custom Odoo 17 ERP migration from Contabo VPS to Google Cloud Platform.

## Project Overview

| Aspect | Details |
|--------|---------|
| Source | Contabo VPS (cvps - 46.250.252.111) |
| Target | Google Cloud Platform (Cloud Run + Cloud SQL) |
| Odoo Version | 17.0 |
| Status | Running in production on Contabo |

## Current Infrastructure (Contabo VPS)

**Server:** cvps (46.250.252.111)
**Path:** `/home/as/ws/odoo`

```
Docker Compose Services:
├── odoo         # Odoo 17 application (port 8069, 8072)
├── psql         # PostgreSQL 15
├── redis        # Redis 7 (caching)
└── mailhog      # Email testing (port 1025, 8025)
```

**Size:**
- Database: 154 MB
- Addons: 1.1 GB (612+ modules)
- Filestore: 244 MB

## Custom Addons

Key custom modules in `/home/as/ws/odoo/addons`:
- `advanced_analytics` - Business analytics
- `advanced_crm` - CRM enhancements
- `advanced_inventory` - Inventory management
- `advanced_reports` - Custom reporting

## SSH Access

```bash
ssh cvps                           # Connect as root
cd /home/as/ws/odoo               # Odoo directory
docker compose ps                  # Check container status
docker compose logs -f odoo        # View Odoo logs
```

## Database Credentials (Production)

```
Host: psql (Docker service)
Port: 5432
Database: odoo
User: odoo
Password: uGajfshoU4YSvpRWoF9uNBtGdDBNI
```

## Target Architecture (GCP)

```
Google Cloud Platform
├── Cloud Run (Odoo application)
│   └── Custom Odoo Docker image
├── Cloud SQL (PostgreSQL 15)
│   └── Migrated database (154 MB)
├── Cloud Storage (GCS)
│   └── Filestore attachments (244 MB)
├── Cloud CDN (optional)
│   └── Static assets
├── Cloud Load Balancer
│   └── HTTPS termination
├── VPC Connector
│   └── Cloud SQL private connection
└── Secret Manager
    └── DB password, admin password
```

## Migration Tasks

### Phase 1: Code Management
- [x] Create local project structure
- [ ] Set up GitHub repository
- [ ] Push Contabo code to GitHub
- [ ] Configure CI/CD with Cloud Build

### Phase 2: GCP Infrastructure
- [ ] Apply Terraform for Cloud SQL, VPC, GCS
- [ ] Create secrets in Secret Manager
- [ ] Configure VPC connector for Cloud Run

### Phase 3: Database Migration
- [ ] Export database from Contabo (`pg_dump`)
- [ ] Upload to GCS
- [ ] Import to Cloud SQL (`pg_restore`)
- [ ] Verify data integrity

### Phase 4: Filestore Migration
- [ ] Export filestore from Contabo
- [ ] Upload to GCS bucket
- [ ] Update `ir.attachment` records for GCS

### Phase 5: Application Deployment
- [ ] Build Docker image from Contabo code
- [ ] Push to Artifact Registry
- [ ] Deploy to Cloud Run
- [ ] Configure Cloud SQL connection

### Phase 6: DNS & Cutover
- [ ] Configure Load Balancer
- [ ] Set up managed SSL certificate
- [ ] Update DNS (Cloudflare)
- [ ] Test and verify
- [ ] Decommission Contabo

## Commands

### On Contabo (cvps)
```bash
# Check Odoo status
ssh cvps "docker compose -f /home/as/ws/odoo/docker-compose.yml ps"

# View logs
ssh cvps "docker compose -f /home/as/ws/odoo/docker-compose.yml logs -f odoo"

# Backup database
ssh cvps "docker exec odoo-psql-1 pg_dump -U odoo -d odoo -Fc > /tmp/odoo_backup.dump"

# Backup filestore
ssh cvps "tar -czf /tmp/odoo_filestore.tar.gz -C /home/as/ws/odoo/var ."
```

### Local Development
```bash
cd /Users/pk/Documents/ws/odoo
docker-compose up -d
open http://localhost:8069
```

### GCP Deployment
```bash
# Apply infrastructure
cd terraform && terraform apply

# Build and deploy
gcloud builds submit --config=cloudbuild.yaml
```

## Notes

- Odoo requires persistent database connections - Cloud Run min-instances=1
- Workers set to 4 in production config
- Email currently via Mailhog (need to configure SMTP for production)
- Proxy mode disabled - enable for Cloud Run behind load balancer
- Current domain: needs verification from Cloudflare setup
