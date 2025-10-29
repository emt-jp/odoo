# Docker & Docker Compose Setup for Odoo Enterprise Features

This repository includes a complete Docker and Docker Compose setup for running Odoo with all the enterprise features we've built.

## 🐳 **Quick Start**

### **1. Prerequisites**
- Docker 20.10+ 
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB free disk space

### **2. Clone and Setup**
```bash
git clone <repository-url>
cd odoo
```

### **3. Start the System**
```bash
# Build and start all services
make build
make up

# Or using Docker Compose directly
docker-compose up -d
```

### **4. Access the Application**
- **Odoo**: http://localhost:8069
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Flower**: http://localhost:5555
- **Mailhog**: http://localhost:8025
- **PgAdmin**: http://localhost:5050 (admin@odoo.com/admin)

## 🏗️ **Architecture Overview**

### **Services Included**

| Service | Port | Description |
|---------|------|-------------|
| **odoo** | 8069 | Main Odoo application |
| **db** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache |
| **nginx** | 80 | Reverse proxy |
| **celery_worker** | - | Background tasks |
| **celery_beat** | - | Scheduled tasks |
| **flower** | 5555 | Celery monitoring |
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3000 | Dashboards |
| **mailhog** | 8025 | Email testing |
| **elasticsearch** | 9200 | Search engine |
| **kibana** | 5601 | Log visualization |
| **minio** | 9000 | Object storage |

### **Docker Compose Files**

- **`docker-compose.yml`** - Main production configuration
- **`docker-compose.override.yml`** - Development overrides
- **`docker-compose.test.yml`** - Testing configuration
- **`docker-compose.prod.yml`** - Production overrides

## 🚀 **Development Workflow**

### **1. Start Development Environment**
```bash
# Start with development profile
make dev-up

# Or manually
docker-compose --profile dev up -d
```

### **2. Access Development Tools**
```bash
# Open shell in Odoo container
make shell

# View logs
make logs

# Access database
make db-shell

# Access Redis
make redis-shell
```

### **3. Install Enterprise Modules**
```bash
# Install all enterprise modules
make install-modules

# Or install specific modules
docker-compose exec odoo python3 odoo-bin -c /etc/odoo/odoo.conf -i advanced_analytics,advanced_crm -d odoo --stop-after-init
```

### **4. Code Development**
```bash
# Format code
make format

# Lint code
make lint

# Install dependencies
make install
```

## 🧪 **Testing**

### **1. Run All Tests**
```bash
# Run all tests
make test

# Or using the test script
./tools/scripts/test.sh all
```

### **2. Run Specific Test Types**
```bash
# Unit tests only
make test-unit
./tools/scripts/test.sh unit

# Integration tests only
make test-integration
./tools/scripts/test.sh integration

# End-to-end tests only
make test-e2e
./tools/scripts/test.sh e2e

# Performance tests only
make test-performance
./tools/scripts/test.sh performance

# Security tests only
make test-security
./tools/scripts/test.sh security
```

### **3. Run Tests for Specific Module**
```bash
# Test specific module
./tools/scripts/test.sh module vehicle_management

# Test with specific marker
./tools/scripts/test.sh marker enterprise
```

### **4. View Test Results**
```bash
# Generate coverage report
make test-coverage

# View results
open test_results/htmlcov/index.html
open test_results/report.html
```

## 📊 **Monitoring & Observability**

### **1. Metrics & Dashboards**
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - Pre-configured dashboards for Odoo, PostgreSQL, Redis

### **2. Logs & Search**
- **Kibana**: http://localhost:5601
  - Elasticsearch integration for log analysis
  - Real-time log streaming

### **3. Application Monitoring**
- **Prometheus**: http://localhost:9090
  - Metrics collection and storage
  - Custom Odoo metrics

- **Flower**: http://localhost:5555
  - Celery task monitoring
  - Background job status

### **4. Database Management**
- **PgAdmin**: http://localhost:5050
  - Username: `admin@odoo.com`
  - Password: `admin`
  - Full PostgreSQL management

## 🔧 **Configuration**

### **1. Environment Variables**
Create `.env` file for custom configuration:
```bash
# Database
POSTGRES_DB=odoo
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo

# Redis
REDIS_PASSWORD=odoo_redis_password

# Odoo
ODOO_ADMIN_PASSWORD=admin
ODOO_ENTERPRISE_MODE=true
ODOO_LICENSE_KEY=TRIAL-0000-0000-0000
```

### **2. Odoo Configuration**
Edit `ops/config/odoo.conf` for Odoo-specific settings:
```ini
[options]
admin_passwd = admin
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
enterprise_mode = True
license_key = TRIAL-0000-0000-0000
```

### **3. Nginx Configuration**
Edit `ops/docker/nginx/nginx.conf` for web server settings.

## 🗄️ **Database Management**

### **1. Database Operations**
```bash
# Initialize database
make db-init

# Reset database
make db-reset

# Backup database
make db-backup

# Restore database
make db-restore
```

### **2. Database Access**
```bash
# Connect to database
make db-shell

# Or directly
docker-compose exec db psql -U odoo -d odoo
```

## 🔒 **Security**

### **1. Security Scanning**
```bash
# Run security scans
make security-scan

# Check for vulnerabilities
docker-compose exec odoo safety check
```

### **2. SSL/TLS Configuration**
For production, configure SSL certificates:
```bash
# Place certificates in ops/docker/nginx/ssl/
# Update nginx configuration
```

## 📈 **Performance**

### **1. Performance Testing**
```bash
# Run performance tests
make test-performance

# Profile application
make profile

# Memory profiling
make memory-profile
```

### **2. Load Testing**
```bash
# Using Locust (if configured)
docker-compose exec odoo locust -f tests/performance/locustfile.py
```

## 🚀 **Production Deployment**

### **1. Production Build**
```bash
# Build production images
make prod-build

# Start production services
make prod-up
```

### **2. Production Configuration**
- Use `docker-compose.prod.yml` for production overrides
- Configure proper secrets management
- Set up SSL certificates
- Configure backup strategies

## 🧹 **Maintenance**

### **1. Cleanup**
```bash
# Clean up containers and volumes
make clean

# Clean up specific resources
docker-compose down -v
docker system prune -f
```

### **2. Updates**
```bash
# Update modules
make upgrade-modules

# Rebuild images
make build
```

### **3. Backups**
```bash
# Backup everything
make backup-all

# Restore from backup
make restore-all
```

## 🐛 **Troubleshooting**

### **1. Common Issues**

#### **Database Connection Issues**
```bash
# Check database status
docker-compose exec db pg_isready -U odoo

# Check database logs
make logs-db
```

#### **Odoo Not Starting**
```bash
# Check Odoo logs
make logs-odoo

# Check configuration
docker-compose exec odoo python3 odoo-bin -c /etc/odoo/odoo.conf --test-enable
```

#### **Memory Issues**
```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.yml
```

### **2. Debug Mode**
```bash
# Start with debug mode
docker-compose exec odoo python3 odoo-bin -c /etc/odoo/odoo.conf --dev=reload,qweb,werkzeug,xml --log-level=debug
```

### **3. Health Checks**
```bash
# Check all services
make health

# Check specific service
curl -f http://localhost:8069/web/health
```

## 📚 **Available Commands**

### **Development Commands**
```bash
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make restart        # Restart all services
make logs           # Show logs
make shell          # Open shell
```

### **Testing Commands**
```bash
make test           # Run all tests
make test-unit      # Unit tests
make test-integration # Integration tests
make test-e2e       # End-to-end tests
make test-coverage  # Coverage report
```

### **Database Commands**
```bash
make db-init        # Initialize database
make db-reset       # Reset database
make db-backup      # Backup database
make db-restore     # Restore database
```

### **Utility Commands**
```bash
make clean          # Clean up
make lint           # Code linting
make format         # Format code
make install        # Install dependencies
```

## 🎯 **Best Practices**

### **1. Development**
- Use development profile for local development
- Run tests before committing code
- Use proper branch naming conventions
- Keep Docker images updated

### **2. Testing**
- Write comprehensive unit tests
- Include integration tests for critical paths
- Use test fixtures for consistent data
- Monitor test coverage

### **3. Production**
- Use production configuration
- Set up proper monitoring
- Configure automated backups
- Use secrets management

### **4. Security**
- Regular security scans
- Keep dependencies updated
- Use proper authentication
- Monitor for vulnerabilities

## 🆘 **Support**

### **Getting Help**
- Check logs: `make logs`
- Check health: `make health`
- Review documentation
- Check GitHub issues

### **Common Solutions**
- Restart services: `make restart`
- Reset database: `make db-reset`
- Clean up: `make clean`
- Rebuild: `make build`

---

**Happy Dockerizing! 🐳✨**




