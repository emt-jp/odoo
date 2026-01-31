#!/bin/bash
# SSH-based database export and import script
# Exports database from od.emoment.tech via SSH and imports to Docker

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REMOTE_HOST="od.emoment.tech"
REMOTE_USER=""  # Will prompt if empty
REMOTE_SSH_KEY=""  # Optional: path to SSH key
REMOTE_DB="odoo"  # Update if different
REMOTE_DB_USER="odoo"  # Update if different
REMOTE_ODOO_PATH="/opt/odoo"  # Common Odoo path, update if different

LOCAL_DB="odoo"
LOCAL_USER="odoo"
LOCAL_PASSWORD="odoo"

BACKUP_DIR="./var/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/odoo_backup_${TIMESTAMP}.dump"

echo "=========================================="
echo "SSH Database Export & Import Tool"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Get SSH credentials
if [ -z "$REMOTE_USER" ]; then
    read -p "Enter SSH username for ${REMOTE_HOST}: " REMOTE_USER
fi

if [ -z "$REMOTE_SSH_KEY" ]; then
    read -p "Enter path to SSH key (or press Enter for password auth): " REMOTE_SSH_KEY
fi

# Build SSH command
if [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    SSH_CMD="ssh -i ${REMOTE_SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST}"
    SCP_CMD="scp -i ${REMOTE_SSH_KEY}"
else
    SSH_CMD="ssh ${REMOTE_USER}@${REMOTE_HOST}"
    SCP_CMD="scp"
fi

echo ""
echo -e "${BLUE}Step 1: Testing SSH connection...${NC}"
if ! $SSH_CMD "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${RED}✗ SSH connection failed!${NC}"
    echo "Please check:"
    echo "  - SSH credentials"
    echo "  - SSH key permissions (chmod 600)"
    echo "  - Network connectivity"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"

echo ""
echo -e "${BLUE}Step 2: Detecting Odoo installation...${NC}"

# Try to find Odoo installation
ODOO_PATH=$($SSH_CMD "find /opt /home /var -name 'odoo-bin' -type f 2>/dev/null | head -1 | xargs dirname 2>/dev/null || echo ''")

if [ -z "$ODOO_PATH" ]; then
    echo -e "${YELLOW}⚠ Could not auto-detect Odoo path${NC}"
    read -p "Enter Odoo installation path on remote server: " ODOO_PATH
else
    echo -e "${GREEN}✓ Found Odoo at: ${ODOO_PATH}${NC}"
fi

# Try to find Odoo config file
CONFIG_FILE=$($SSH_CMD "find ${ODOO_PATH} -name 'odoo.conf' -o -name 'openerp-server.conf' 2>/dev/null | head -1 || echo ''")

if [ -z "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠ Could not find config file${NC}"
    read -p "Enter Odoo config file path: " CONFIG_FILE
fi

# Extract database info from config if possible
if [ -n "$CONFIG_FILE" ]; then
    echo -e "${BLUE}Reading database configuration...${NC}"
    DB_NAME=$($SSH_CMD "grep '^db_name' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '${REMOTE_DB}'")
    DB_USER=$($SSH_CMD "grep '^db_user' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '${REMOTE_DB_USER}'")
    DB_HOST=$($SSH_CMD "grep '^db_host' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo 'localhost'")
    DB_PORT=$($SSH_CMD "grep '^db_port' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '5432'")
    
    if [ -n "$DB_NAME" ] && [ "$DB_NAME" != "False" ]; then
        REMOTE_DB="$DB_NAME"
    fi
    if [ -n "$DB_USER" ] && [ "$DB_USER" != "False" ]; then
        REMOTE_DB_USER="$DB_USER"
    fi
    
    echo -e "${GREEN}✓ Database: ${REMOTE_DB}, User: ${REMOTE_DB_USER}${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Creating database backup on remote server...${NC}"

# Method 1: Try using Odoo's backup feature via command line
echo "Attempting to create backup using Odoo CLI..."

# Check if we can use odoo-bin backup
BACKUP_CMD="$SSH_CMD \"cd ${ODOO_PATH} && python3 odoo-bin -c ${CONFIG_FILE} --database=${REMOTE_DB} --backup=${BACKUP_FILE} --stop-after-init 2>&1 || echo 'CLI_BACKUP_FAILED'\""

if $SSH_CMD "cd ${ODOO_PATH} && test -f odoo-bin" 2>/dev/null; then
    echo "Creating backup via Odoo CLI..."
    REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.dump"
    
    $SSH_CMD "cd ${ODOO_PATH} && python3 odoo-bin -c ${CONFIG_FILE} -d ${REMOTE_DB} --backup=${REMOTE_BACKUP} --stop-after-init" || {
        echo -e "${YELLOW}⚠ Odoo CLI backup failed, trying pg_dump...${NC}"
        REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.sql"
        
        # Get database password from config or prompt
        DB_PASSWORD=$($SSH_CMD "grep '^db_password' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo ''")
        
        if [ -z "$DB_PASSWORD" ]; then
            read -sp "Enter database password for ${REMOTE_DB_USER}: " DB_PASSWORD
            echo ""
        fi
        
        # Use pg_dump
        $SSH_CMD "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${REMOTE_DB_USER} -d ${REMOTE_DB} -F c -f ${REMOTE_BACKUP}" || {
            echo -e "${RED}✗ Database backup failed!${NC}"
            echo "Trying alternative method..."
            
            # Alternative: Use Odoo's web backup
            echo -e "${YELLOW}Please create backup manually:${NC}"
            echo "1. Go to: https://${REMOTE_HOST}/web/database/manager"
            echo "2. Click 'Backup' for database: ${REMOTE_DB}"
            echo "3. Download the backup file"
            echo "4. Place it in: ${BACKUP_DIR}/"
            read -p "Press Enter after downloading backup..."
            
            # List available backups
            echo "Available backup files:"
            ls -lh "${BACKUP_DIR}"/*.dump "${BACKUP_DIR}"/*.zip 2>/dev/null || echo "No backup files found"
            read -p "Enter backup filename (relative to ${BACKUP_DIR}/): " BACKUP_FILE
            BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
            
            if [ ! -f "${BACKUP_FILE}" ]; then
                echo -e "${RED}✗ Backup file not found!${NC}"
                exit 1
            fi
            
            REMOTE_BACKUP=""
        }
    }
else
    # Direct pg_dump
    echo "Using pg_dump directly..."
    REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.dump"
    
    DB_PASSWORD=$($SSH_CMD "grep '^db_password' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo ''")
    
    if [ -z "$DB_PASSWORD" ]; then
        read -sp "Enter database password for ${REMOTE_DB_USER}: " DB_PASSWORD
        echo ""
    fi
    
    $SSH_CMD "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${REMOTE_DB_USER} -d ${REMOTE_DB} -F c -f ${REMOTE_BACKUP}" || {
        echo -e "${RED}✗ Database backup failed!${NC}"
        exit 1
    }
fi

if [ -n "$REMOTE_BACKUP" ]; then
    echo -e "${GREEN}✓ Backup created on remote: ${REMOTE_BACKUP}${NC}"
    
    echo ""
    echo -e "${BLUE}Step 4: Downloading backup file...${NC}"
    
    # Download backup file
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BACKUP}" "${BACKUP_FILE}" || {
        echo -e "${RED}✗ Failed to download backup!${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Backup downloaded: ${BACKUP_FILE}${NC}"
    
    # Clean up remote backup
    echo "Cleaning up remote backup..."
    $SSH_CMD "rm -f ${REMOTE_BACKUP}"
fi

echo ""
echo -e "${BLUE}Step 5: Restoring to local Docker instance...${NC}"

# Stop Odoo
echo "Stopping Odoo container..."
docker-compose stop odoo || true

# Wait a moment
sleep 2

# Drop and recreate database
echo "Preparing local database..."
docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${LOCAL_DB};" 2>/dev/null || true
docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "CREATE DATABASE ${LOCAL_DB};"

# Determine backup format
if [[ "${BACKUP_FILE}" == *.dump ]] || [[ "${BACKUP_FILE}" == *.sql ]]; then
    FORMAT="custom"
else
    # Check file type
    FILE_TYPE=$(file "${BACKUP_FILE}" | grep -o "PostgreSQL\|SQL\|Zip")
    if [[ "$FILE_TYPE" == *"PostgreSQL"* ]] || [[ "$FILE_TYPE" == *"custom"* ]]; then
        FORMAT="custom"
    elif [[ "$FILE_TYPE" == *"SQL"* ]] || [[ "$FILE_TYPE" == *"ASCII"* ]]; then
        FORMAT="plain"
    elif [[ "$FILE_TYPE" == *"Zip"* ]] || [[ "${BACKUP_FILE}" == *.zip ]]; then
        echo -e "${YELLOW}⚠ ZIP file detected. Extracting...${NC}"
        unzip -o "${BACKUP_FILE}" -d "${BACKUP_DIR}"/
        BACKUP_FILE=$(find "${BACKUP_DIR}" -name "*.dump" -o -name "*.sql" | head -1)
        if [ -z "$BACKUP_FILE" ]; then
            echo -e "${RED}✗ Could not find database file in ZIP!${NC}"
            exit 1
        fi
        FORMAT="custom"
    else
        FORMAT="custom"  # Default to custom
    fi
fi

echo "Backup format: ${FORMAT}"
echo "Backup file: ${BACKUP_FILE}"

# Restore database
echo "Restoring database..."
if [ "$FORMAT" == "custom" ]; then
    cat "${BACKUP_FILE}" | docker-compose exec -T db pg_restore -U "${LOCAL_USER}" -d "${LOCAL_DB}" --no-owner --no-acl -v 2>&1 | tail -20 || {
        echo -e "${YELLOW}⚠ Some warnings during restore (this may be normal)${NC}"
    }
else
    cat "${BACKUP_FILE}" | docker-compose exec -T db psql -U "${LOCAL_USER}" -d "${LOCAL_DB}" > /dev/null 2>&1
fi

echo -e "${GREEN}✓ Database restored${NC}"

# Start Odoo
echo "Starting Odoo container..."
docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Database Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Wait for Odoo to start (check: docker-compose logs odoo --tail=50)"
echo "2. Access Odoo at: http://localhost:8069"
echo "3. Login with your remote database credentials"
echo "4. Update modules if needed:"
echo "   python3 upgrade_module.py"
echo ""
echo "Backup file saved at: ${BACKUP_FILE}"

