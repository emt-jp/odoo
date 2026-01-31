#!/bin/bash
# Automated migration script that uses environment variables or prompts
# Usage: REMOTE_SSH_USER=user REMOTE_SSH_KEY=/path/to/key ./migrate_from_remote_auto.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

REMOTE_HOST="${REMOTE_HOST:-od.emoment.tech}"
BACKUP_DIR="./var/backups"
mkdir -p "${BACKUP_DIR}"

# Load config if exists
if [ -f .migration_config ]; then
    echo "Loading configuration from .migration_config..."
    source .migration_config
fi

REMOTE_HOST="${REMOTE_HOST:-od.emoment.tech}"

echo "=========================================="
echo "Automated Database Migration"
echo "${REMOTE_HOST} → Docker"
echo "=========================================="
echo ""

# Get SSH credentials
if [ -z "$REMOTE_SSH_USER" ]; then
    read -p "SSH Username for ${REMOTE_HOST}: " REMOTE_SSH_USER
fi

if [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    SSH_CMD="ssh -i ${REMOTE_SSH_KEY} -o StrictHostKeyChecking=no -o BatchMode=yes"
    SCP_CMD="scp -i ${REMOTE_SSH_KEY} -o StrictHostKeyChecking=no -o BatchMode=yes"
    echo "Using SSH key: ${REMOTE_SSH_KEY}"
    # Test connection with key
    echo ""
    echo -e "${YELLOW}Testing SSH connection...${NC}"
    if ! timeout 10 $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "echo 'Connected'" 2>/dev/null; then
        echo -e "${RED}✗ SSH connection failed!${NC}"
        echo "Please check:"
        echo "  - SSH credentials"
        echo "  - Network connectivity"
        echo "  - SSH key permissions (chmod 600)"
        exit 1
    fi
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    SSH_CMD="ssh -o StrictHostKeyChecking=no"
    SCP_CMD="scp -o StrictHostKeyChecking=no"
    echo "Using password authentication"
    echo -e "${YELLOW}Note: You will be prompted for SSH password during the migration${NC}"
    # Skip connection test for password auth - it will prompt during actual operations
fi

# Detect Odoo
echo ""
echo -e "${BLUE}Detecting Odoo installation...${NC}"
ODOO_PATH=$($SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "
    for p in /opt/odoo /home/odoo /var/lib/odoo; do
        [ -f \"\$p/odoo-bin\" ] && echo \"\$p\" && exit 0
    done
    find /opt /home -name 'odoo-bin' 2>/dev/null | head -1 | xargs dirname 2>/dev/null
" 2>/dev/null | head -1)

if [ -z "$ODOO_PATH" ]; then
    echo -e "${YELLOW}⚠ Auto-detection failed${NC}"
    read -p "Enter Odoo path: " ODOO_PATH
fi
echo -e "${GREEN}✓ Odoo: ${ODOO_PATH}${NC}"

# Get config
CONFIG_FILE=$($SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "
    find ${ODOO_PATH} -name 'odoo.conf' 2>/dev/null | head -1 || echo '${ODOO_PATH}/odoo.conf'
" 2>/dev/null | head -1)

# Read DB config
echo "Reading database configuration..."
DB_CONFIG=$($SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "
    [ -f '${CONFIG_FILE}' ] && grep -E '^(db_name|db_user|db_host|db_port|db_password)=' '${CONFIG_FILE}' 2>/dev/null
" 2>/dev/null)

DB_NAME=$(echo "$DB_CONFIG" | grep "^db_name" | cut -d'=' -f2 | tr -d ' ' | grep -v "^False$" | head -1 || echo "${REMOTE_DB_NAME:-odoo}")
DB_USER=$(echo "$DB_CONFIG" | grep "^db_user" | cut -d'=' -f2 | tr -d ' ' | grep -v "^False$" | head -1 || echo "${REMOTE_DB_USER:-odoo}")
DB_HOST=$(echo "$DB_CONFIG" | grep "^db_host" | cut -d'=' -f2 | tr -d ' ' | grep -v "^False$" | head -1 || echo "localhost")
DB_PORT=$(echo "$DB_CONFIG" | grep "^db_port" | cut -d'=' -f2 | tr -d ' ' | grep -v "^False$" | head -1 || echo "5432")
DB_PASSWORD=$(echo "$DB_CONFIG" | grep "^db_password" | cut -d'=' -f2 | tr -d ' ' | grep -v "^False$" | head -1 || echo "${REMOTE_DB_PASSWORD}")

if [ -z "$DB_NAME" ]; then DB_NAME="odoo"; fi
if [ -z "$DB_USER" ]; then DB_USER="odoo"; fi
if [ -z "$DB_HOST" ]; then DB_HOST="localhost"; fi

echo -e "${GREEN}✓ DB: ${DB_NAME}, User: ${DB_USER}, Host: ${DB_HOST}${NC}"

if [ -z "$DB_PASSWORD" ]; then
    read -sp "Database password: " DB_PASSWORD
    echo ""
fi

# Create backup
echo ""
echo -e "${BLUE}Creating backup...${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.dump"

# Try Odoo CLI
if $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "cd ${ODOO_PATH} && test -f odoo-bin" 2>/dev/null; then
    echo "Using Odoo CLI..."
    $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "cd ${ODOO_PATH} && python3 odoo-bin -c ${CONFIG_FILE} -d ${DB_NAME} --backup=${REMOTE_BACKUP} --stop-after-init" 2>&1 | grep -v "WARNING\|INFO" || {
        echo "Falling back to pg_dump..."
        $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -F c -f ${REMOTE_BACKUP}" 2>/dev/null
    }
else
    echo "Using pg_dump..."
    $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -F c -f ${REMOTE_BACKUP}" 2>/dev/null
fi

if ! $SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "test -f ${REMOTE_BACKUP}" 2>/dev/null; then
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi

BACKUP_SIZE=$($SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "du -h ${REMOTE_BACKUP} | cut -f1" 2>/dev/null)
echo -e "${GREEN}✓ Backup created: ${BACKUP_SIZE}${NC}"

# Download
echo ""
echo -e "${BLUE}Downloading backup...${NC}"
LOCAL_BACKUP="${BACKUP_DIR}/odoo_backup_${TIMESTAMP}.dump"
$SCP_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}:${REMOTE_BACKUP}" "${LOCAL_BACKUP}" 2>/dev/null || {
    echo -e "${RED}✗ Download failed!${NC}"
    exit 1
}
echo -e "${GREEN}✓ Downloaded: ${LOCAL_BACKUP}${NC}"

# Cleanup remote
$SSH_CMD "${REMOTE_SSH_USER}@${REMOTE_HOST}" "rm -f ${REMOTE_BACKUP}" 2>/dev/null

# Restore
echo ""
echo -e "${BLUE}Restoring to Docker...${NC}"
docker-compose stop odoo 2>/dev/null || true
sleep 2

docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;" 2>/dev/null || true
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;" 2>/dev/null || true

echo "Restoring (this may take a few minutes)..."
cat "${LOCAL_BACKUP}" | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl -v 2>&1 | tail -10

docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration Complete!"
echo "==========================================${NC}"
echo "Backup: ${LOCAL_BACKUP}"
echo "Access: http://localhost:8069"
echo ""

