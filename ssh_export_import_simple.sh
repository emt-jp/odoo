#!/bin/bash
# Simplified SSH export/import script
# Assumes you have SSH access configured

set -e

# Configuration - UPDATE THESE
REMOTE_HOST="od.emoment.tech"
REMOTE_USER=""  # Your SSH username
REMOTE_SSH_KEY=""  # Path to SSH key (optional, leave empty for password auth)
REMOTE_DB="odoo"  # Database name on remote
REMOTE_DB_USER="odoo"  # Database user on remote

LOCAL_DB="odoo"
LOCAL_USER="odoo"

BACKUP_DIR="./var/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.dump"
LOCAL_BACKUP="${BACKUP_DIR}/odoo_backup_${TIMESTAMP}.dump"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "SSH Database Export & Import"
echo "=========================================="
echo ""

# Get credentials
if [ -z "$REMOTE_USER" ]; then
    read -p "SSH Username for ${REMOTE_HOST}: " REMOTE_USER
fi

if [ -z "$REMOTE_SSH_KEY" ]; then
    read -p "SSH Key path (or Enter for password auth): " REMOTE_SSH_KEY
fi

# Build SSH/SCP commands
if [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    SSH="ssh -i ${REMOTE_SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST}"
    SCP="scp -i ${REMOTE_SSH_KEY}"
else
    SSH="ssh ${REMOTE_USER}@${REMOTE_HOST}"
    SCP="scp"
fi

mkdir -p "${BACKUP_DIR}"

echo -e "${YELLOW}Step 1: Testing SSH connection...${NC}"
if ! $SSH "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${RED}✗ SSH connection failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connected${NC}"

echo ""
echo -e "${YELLOW}Step 2: Finding Odoo installation...${NC}"

# Try common Odoo paths
ODOO_PATHS=(
    "/opt/odoo"
    "/home/odoo"
    "/var/lib/odoo"
    "$HOME/odoo"
)

ODOO_PATH=""
for path in "${ODOO_PATHS[@]}"; do
    if $SSH "test -d ${path} && test -f ${path}/odoo-bin" 2>/dev/null; then
        ODOO_PATH="$path"
        break
    fi
done

if [ -z "$ODOO_PATH" ]; then
    ODOO_PATH=$($SSH "find /opt /home /var -name 'odoo-bin' -type f 2>/dev/null | head -1 | xargs dirname 2>/dev/null || echo ''")
fi

if [ -z "$ODOO_PATH" ]; then
    read -p "Enter Odoo installation path: " ODOO_PATH
fi

echo -e "${GREEN}✓ Odoo path: ${ODOO_PATH}${NC}"

# Find config file
CONFIG_FILE=$($SSH "find ${ODOO_PATH} -name 'odoo.conf' -o -name 'openerp-server.conf' 2>/dev/null | head -1 || echo ''")
if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="${ODOO_PATH}/odoo.conf"
fi

# Read database config
echo -e "${YELLOW}Step 3: Reading database configuration...${NC}"
DB_NAME=$($SSH "grep '^db_name' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '${REMOTE_DB}'")
DB_USER=$($SSH "grep '^db_user' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '${REMOTE_DB_USER}'")
DB_HOST=$($SSH "grep '^db_host' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo 'localhost'")
DB_PORT=$($SSH "grep '^db_port' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '5432'")
DB_PASSWORD=$($SSH "grep '^db_password' ${CONFIG_FILE} 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo ''")

if [ -n "$DB_NAME" ] && [ "$DB_NAME" != "False" ]; then
    REMOTE_DB="$DB_NAME"
fi
if [ -n "$DB_USER" ] && [ "$DB_USER" != "False" ]; then
    REMOTE_DB_USER="$DB_USER"
fi

echo -e "${GREEN}✓ Database: ${REMOTE_DB}, User: ${REMOTE_DB_USER}, Host: ${DB_HOST}${NC}"

# Get password if not in config
if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" == "False" ]; then
    read -sp "Database password for ${REMOTE_DB_USER}: " DB_PASSWORD
    echo ""
fi

echo ""
echo -e "${YELLOW}Step 4: Creating backup on remote server...${NC}"

# Try Odoo CLI backup first
if $SSH "cd ${ODOO_PATH} && test -f odoo-bin" 2>/dev/null; then
    echo "Trying Odoo CLI backup..."
    $SSH "cd ${ODOO_PATH} && python3 odoo-bin -c ${CONFIG_FILE} -d ${REMOTE_DB} --backup=${REMOTE_BACKUP} --stop-after-init" 2>&1 | grep -v "WARNING\|INFO" || {
        echo "Odoo CLI backup failed, using pg_dump..."
        $SSH "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${REMOTE_DB_USER} -d ${REMOTE_DB} -F c -f ${REMOTE_BACKUP}" || {
            echo -e "${RED}✗ Backup failed!${NC}"
            exit 1
        }
    }
else
    # Use pg_dump directly
    echo "Using pg_dump..."
    $SSH "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${REMOTE_DB_USER} -d ${REMOTE_DB} -F c -f ${REMOTE_BACKUP}" || {
        echo -e "${RED}✗ Backup failed!${NC}"
        exit 1
    }
fi

echo -e "${GREEN}✓ Backup created: ${REMOTE_BACKUP}${NC}"

echo ""
echo -e "${YELLOW}Step 5: Downloading backup...${NC}"
$SCP "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BACKUP}" "${LOCAL_BACKUP}" || {
    echo -e "${RED}✗ Download failed!${NC}"
    exit 1
}
echo -e "${GREEN}✓ Downloaded: ${LOCAL_BACKUP}${NC}"

# Cleanup remote
$SSH "rm -f ${REMOTE_BACKUP}"

echo ""
echo -e "${YELLOW}Step 6: Restoring to Docker...${NC}"

# Stop Odoo
docker-compose stop odoo 2>/dev/null || true
sleep 2

# Recreate database
echo "Recreating database..."
docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${LOCAL_DB};" 2>/dev/null || true
docker-compose exec -T db psql -U "${LOCAL_USER}" -d postgres -c "CREATE DATABASE ${LOCAL_DB};"

# Restore
echo "Restoring backup..."
cat "${LOCAL_BACKUP}" | docker-compose exec -T db pg_restore -U "${LOCAL_USER}" -d "${LOCAL_DB}" --no-owner --no-acl -v 2>&1 | tail -10

echo -e "${GREEN}✓ Database restored${NC}"

# Start Odoo
echo "Starting Odoo..."
docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Backup saved: ${LOCAL_BACKUP}"
echo "Access Odoo: http://localhost:8069"
echo "Check logs: docker-compose logs odoo --tail=50"

