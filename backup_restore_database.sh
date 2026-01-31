#!/bin/bash
# Database backup and restore script for Odoo
# This script helps export database from remote and import to Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REMOTE_HOST="od.emoment.tech"
REMOTE_DB="odoo"  # Update with your database name
REMOTE_USER="odoo"  # Update with your database user
REMOTE_PASSWORD=""  # Will prompt if empty

LOCAL_DB="odoo"
LOCAL_USER="odoo"
LOCAL_PASSWORD="odoo"
LOCAL_HOST="localhost"
LOCAL_PORT="5432"

BACKUP_DIR="./var/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/odoo_backup_${TIMESTAMP}.sql"

echo "=========================================="
echo "Odoo Database Backup & Restore Tool"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Function to backup from remote
backup_remote() {
    echo -e "${GREEN}📦 Backing up database from remote...${NC}"
    
    if [ -z "$REMOTE_PASSWORD" ]; then
        read -sp "Enter remote database password: " REMOTE_PASSWORD
        echo ""
    fi
    
    # Using pg_dump over SSH or direct connection
    echo "Choose backup method:"
    echo "1) Direct PostgreSQL connection (if accessible)"
    echo "2) Via Odoo backup feature (recommended)"
    read -p "Enter choice (1 or 2): " method
    
    if [ "$method" == "1" ]; then
        echo "Attempting direct PostgreSQL connection..."
        PGPASSWORD="${REMOTE_PASSWORD}" pg_dump -h "${REMOTE_HOST}" -U "${REMOTE_USER}" -d "${REMOTE_DB}" -F c -f "${BACKUP_FILE}.dump" || {
            echo -e "${RED}✗ Direct connection failed. Try method 2.${NC}"
            exit 1
        }
        echo -e "${GREEN}✓ Backup created: ${BACKUP_FILE}.dump${NC}"
    else
        echo -e "${YELLOW}Please use Odoo's backup feature:${NC}"
        echo "1. Go to: https://${REMOTE_HOST}/web/database/manager"
        echo "2. Click 'Backup' for your database"
        echo "3. Download the backup file"
        echo "4. Place it in: ${BACKUP_DIR}/"
        echo ""
        read -p "Press Enter after you've downloaded the backup..."
        
        # List available backups
        echo "Available backup files:"
        ls -lh "${BACKUP_DIR}"/*.dump "${BACKUP_DIR}"/*.zip 2>/dev/null || echo "No backup files found"
        read -p "Enter backup filename (or full path): " BACKUP_FILE
    fi
}

# Function to restore to local Docker
restore_local() {
    echo -e "${GREEN}📥 Restoring database to local Docker...${NC}"
    
    if [ ! -f "${BACKUP_FILE}" ] && [ ! -f "${BACKUP_FILE}.dump" ]; then
        echo -e "${RED}✗ Backup file not found!${NC}"
        exit 1
    fi
    
    # Determine backup file
    if [ -f "${BACKUP_FILE}.dump" ]; then
        RESTORE_FILE="${BACKUP_FILE}.dump"
        FORMAT="custom"
    elif [ -f "${BACKUP_FILE}" ]; then
        RESTORE_FILE="${BACKUP_FILE}"
        if [[ "${BACKUP_FILE}" == *.dump ]]; then
            FORMAT="custom"
        else
            FORMAT="plain"
        fi
    else
        echo -e "${RED}✗ Backup file not found: ${BACKUP_FILE}${NC}"
        exit 1
    fi
    
    echo "Backup file: ${RESTORE_FILE}"
    echo "Format: ${FORMAT}"
    
    # Stop Odoo container
    echo "Stopping Odoo container..."
    docker-compose stop odoo || true
    
    # Drop and recreate database
    echo "Preparing database..."
    docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${LOCAL_DB};" || true
    docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "CREATE DATABASE ${LOCAL_DB};"
    
    # Restore database
    echo "Restoring database..."
    if [ "$FORMAT" == "custom" ]; then
        docker-compose exec -T db pg_restore -U "${LOCAL_USER}" -d "${LOCAL_DB}" --no-owner --no-acl < "${RESTORE_FILE}" || {
            # Try alternative method
            cat "${RESTORE_FILE}" | docker-compose exec -T db pg_restore -U "${LOCAL_USER}" -d "${LOCAL_DB}" --no-owner --no-acl
        }
    else
        cat "${RESTORE_FILE}" | docker-compose exec -T db psql -U "${LOCAL_USER}" -d "${LOCAL_DB}" > /dev/null
    fi
    
    # Start Odoo container
    echo "Starting Odoo container..."
    docker-compose start odoo
    
    echo -e "${GREEN}✓ Database restored successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Wait for Odoo to start (check: docker-compose logs odoo)"
    echo "2. Access Odoo at: http://localhost:8069"
    echo "3. Update module if needed: python3 upgrade_module.py"
}

# Main menu
echo "What would you like to do?"
echo "1) Backup database from remote"
echo "2) Restore database to local Docker"
echo "3) Both (backup then restore)"
read -p "Enter choice (1, 2, or 3): " choice

case $choice in
    1)
        backup_remote
        ;;
    2)
        restore_local
        ;;
    3)
        backup_remote
        restore_local
        ;;
    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Operation completed!${NC}"

