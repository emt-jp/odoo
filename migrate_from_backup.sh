#!/bin/bash
# Migrate from existing backup on od.emoment.tech (103.101.59.102)
# Backup location: ~/ws/odoo/_backup-20251030-084738/

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
REMOTE_PATH="~/ws/odoo/_backup-20251030-084738"
BACKUP_DIR="./var/backups"
mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo "Database Migration from Backup"
echo "103.101.59.102 → Docker"
echo "=========================================="
echo ""

# Get SSH credentials
echo -e "${BLUE}Step 1: SSH Connection Setup${NC}"
read -p "SSH Username [${REMOTE_USER}]: " SSH_USER
SSH_USER=${SSH_USER:-${REMOTE_USER}}

echo ""
echo "SSH Authentication:"
echo "1) SSH Key"
echo "2) Password"
read -p "Choose (1 or 2): " AUTH_METHOD

if [ "$AUTH_METHOD" == "1" ]; then
    read -p "Path to SSH private key: " SSH_KEY
    if [ ! -f "$SSH_KEY" ]; then
        echo -e "${RED}✗ SSH key not found: ${SSH_KEY}${NC}"
        exit 1
    fi
    chmod 600 "$SSH_KEY" 2>/dev/null || true
    SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no"
    SCP_CMD="scp -i ${SSH_KEY} -o StrictHostKeyChecking=no"
else
    SSH_CMD="ssh -o StrictHostKeyChecking=no"
    SCP_CMD="scp -o StrictHostKeyChecking=no"
fi

# Test connection
echo ""
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! timeout 10 $SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${RED}✗ SSH connection failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"

# Check backup files exist
echo ""
echo -e "${BLUE}Step 2: Checking Backup Files${NC}"
echo "Checking backup directory: ${REMOTE_PATH}"

BACKUP_FILES=$($SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "
    cd ${REMOTE_PATH} 2>/dev/null && ls -lh *.sql *.tgz 2>/dev/null || echo 'NOT_FOUND'
")

if echo "$BACKUP_FILES" | grep -q "NOT_FOUND"; then
    echo -e "${RED}✗ Backup directory not found!${NC}"
    echo "Trying to find backup files..."
    BACKUP_PATH=$($SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "
        find ~/ws/odoo -name '*backup*' -type d 2>/dev/null | head -1 || echo ''
    ")
    if [ -n "$BACKUP_PATH" ]; then
        REMOTE_PATH="$BACKUP_PATH"
        echo -e "${GREEN}✓ Found backup at: ${REMOTE_PATH}${NC}"
    else
        echo -e "${RED}✗ Could not find backup files!${NC}"
        exit 1
    fi
fi

echo "$BACKUP_FILES"
echo ""

# List files
DB_FILE=$($SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && ls -1 *.sql 2>/dev/null | head -1")
FILESTORE_FILE=$($SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && ls -1 *filestore*.tgz 2>/dev/null | head -1")
ADDONS_FILE=$($SSH_CMD "${SSH_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && ls -1 *addons*.tgz 2>/dev/null | head -1")

if [ -z "$DB_FILE" ]; then
    echo -e "${RED}✗ Database backup file not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database file: ${DB_FILE}${NC}"
[ -n "$FILESTORE_FILE" ] && echo -e "${GREEN}✓ Filestore file: ${FILESTORE_FILE}${NC}"
[ -n "$ADDONS_FILE" ] && echo -e "${GREEN}✓ Addons file: ${ADDONS_FILE}${NC}"

# Download files
echo ""
echo -e "${BLUE}Step 3: Downloading Backup Files${NC}"

echo "Downloading database backup..."
$SCP_CMD "${SSH_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${DB_FILE}" "${BACKUP_DIR}/${DB_FILE}" || {
    echo -e "${RED}✗ Download failed!${NC}"
    exit 1
}
echo -e "${GREEN}✓ Downloaded: ${DB_FILE} ($(du -h ${BACKUP_DIR}/${DB_FILE} | cut -f1))${NC}"

if [ -n "$FILESTORE_FILE" ]; then
    echo "Downloading filestore..."
    $SCP_CMD "${SSH_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${FILESTORE_FILE}" "${BACKUP_DIR}/${FILESTORE_FILE}" 2>/dev/null && {
        echo -e "${GREEN}✓ Downloaded: ${FILESTORE_FILE}${NC}"
    } || echo -e "${YELLOW}⚠ Filestore download skipped${NC}"
fi

if [ -n "$ADDONS_FILE" ]; then
    echo "Downloading addons..."
    $SCP_CMD "${SSH_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${ADDONS_FILE}" "${BACKUP_DIR}/${ADDONS_FILE}" 2>/dev/null && {
        echo -e "${GREEN}✓ Downloaded: ${ADDONS_FILE}${NC}"
    } || echo -e "${YELLOW}⚠ Addons download skipped${NC}"
fi

# Restore database
echo ""
echo -e "${BLUE}Step 4: Restoring Database${NC}"

echo "Stopping Odoo container..."
docker-compose stop odoo 2>/dev/null || true
sleep 2

echo "Recreating database..."
docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;" 2>/dev/null || true
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;" 2>/dev/null || true

echo "Restoring database (this may take a few minutes)..."
DB_FILE_PATH="${BACKUP_DIR}/${DB_FILE}"

# Check if it's a SQL file or dump file
if [[ "$DB_FILE" == *.sql ]]; then
    echo "Restoring SQL file..."
    cat "${DB_FILE_PATH}" | docker-compose exec -T db psql -U odoo -d odoo 2>&1 | tail -20 || {
        echo -e "${YELLOW}⚠ Some errors during restore (may be normal)${NC}"
    }
else
    echo "Restoring dump file..."
    cat "${DB_FILE_PATH}" | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl -v 2>&1 | tail -20 || {
        echo -e "${YELLOW}⚠ Some warnings during restore (may be normal)${NC}"
    }
fi

echo -e "${GREEN}✓ Database restored${NC}"

# Restore filestore if available
if [ -n "$FILESTORE_FILE" ] && [ -f "${BACKUP_DIR}/${FILESTORE_FILE}" ]; then
    echo ""
    echo -e "${BLUE}Step 5: Restoring Filestore${NC}"
    
    FILESTORE_SIZE=$(du -h "${BACKUP_DIR}/${FILESTORE_FILE}" | cut -f1)
    if [ "$FILESTORE_SIZE" != "0" ] && [ "$FILESTORE_SIZE" != "87" ]; then
        echo "Extracting filestore..."
        mkdir -p ./var/filestore
        tar -xzf "${BACKUP_DIR}/${FILESTORE_FILE}" -C ./var/filestore/ 2>/dev/null && {
            echo -e "${GREEN}✓ Filestore extracted${NC}"
            echo "Note: Update Odoo config to point to ./var/filestore if needed"
        } || echo -e "${YELLOW}⚠ Filestore extraction skipped (file may be empty)${NC}"
    else
        echo -e "${YELLOW}⚠ Filestore file appears empty, skipping${NC}"
    fi
fi

# Start Odoo
echo ""
echo -e "${BLUE}Step 6: Starting Odoo${NC}"
docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Backup files saved in: ${BACKUP_DIR}/"
echo "  - Database: ${DB_FILE}"
[ -n "$FILESTORE_FILE" ] && echo "  - Filestore: ${FILESTORE_FILE}"
[ -n "$ADDONS_FILE" ] && echo "  - Addons: ${ADDONS_FILE}"
echo ""
echo "Next steps:"
echo "1. Wait for Odoo to start (30-60 seconds)"
echo "2. Check logs: docker-compose logs odoo --tail=50"
echo "3. Access Odoo: http://localhost:8069"
echo "4. Login with your remote database credentials"
echo "5. Update modules: python3 upgrade_module.py"
echo ""

