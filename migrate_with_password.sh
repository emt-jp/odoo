#!/bin/bash
# Migration script that prompts for SSH password
# From: 103.101.59.102 (as@emoment-tech:~/ws/odoo)
# To: Local Docker instance

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
REMOTE_PATH="~/ws/odoo"
BACKUP_DIR="./var/backups"
mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo "Full Migration: Remote → Docker"
echo "From: ${REMOTE_USER}@${REMOTE_HOST}"
echo "=========================================="
echo ""

# SSH will prompt for password automatically
SSH_CMD="ssh -o StrictHostKeyChecking=no"
SCP_CMD="scp -o StrictHostKeyChecking=no"

echo -e "${BLUE}Step 1: Downloading Configuration Files${NC}"
echo -e "${YELLOW}You will be prompted for SSH password for ${REMOTE_USER}@${REMOTE_HOST}${NC}"
echo ""

echo "Downloading docker-compose.yml..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/docker-compose.yml" "./docker-compose.remote.yml" || {
    echo -e "${RED}✗ Failed to download docker-compose.yml${NC}"
    exit 1
}
echo -e "${GREEN}✓ Downloaded docker-compose.yml${NC}"

echo "Downloading odoo.env..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/odoo.env" "./odoo.remote.env" 2>/dev/null && {
    echo -e "${GREEN}✓ Downloaded odoo.env${NC}"
} || echo -e "${YELLOW}⚠ odoo.env not found, skipping${NC}"

# Display remote config
echo ""
echo -e "${BLUE}Remote docker-compose.yml:${NC}"
echo "----------------------------------------"
cat ./docker-compose.remote.yml
echo ""

if [ -f "./odoo.remote.env" ]; then
    echo -e "${BLUE}Remote odoo.env:${NC}"
    echo "----------------------------------------"
    cat ./odoo.remote.env
    echo ""
fi

# Find and download backup files
echo ""
echo -e "${BLUE}Step 2: Finding Backup Files${NC}"
echo -e "${YELLOW}You will be prompted for SSH password again${NC}"

BACKUP_DIR_REMOTE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && ls -d _backup-* 2>/dev/null | head -1 || echo ''")

if [ -z "$BACKUP_DIR_REMOTE" ]; then
    echo -e "${RED}✗ Backup directory not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found backup directory: ${BACKUP_DIR_REMOTE}${NC}"

# List files
echo ""
echo "Backup files:"
$SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -lh *.sql *.tgz 2>/dev/null"

# Get file names
DB_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *.sql 2>/dev/null | head -1")
FILESTORE_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *filestore*.tgz 2>/dev/null | head -1")
ADDONS_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *addons*.tgz 2>/dev/null | head -1")

if [ -z "$DB_FILE" ]; then
    echo -e "${RED}✗ Database backup file not found!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Files to download:${NC}"
echo "  - Database: ${DB_FILE}"
[ -n "$FILESTORE_FILE" ] && echo "  - Filestore: ${FILESTORE_FILE}"
[ -n "$ADDONS_FILE" ] && echo "  - Addons: ${ADDONS_FILE}"

# Download files
echo ""
echo -e "${BLUE}Step 3: Downloading Backup Files${NC}"
echo -e "${YELLOW}You will be prompted for SSH password for each file${NC}"

echo ""
echo "Downloading database backup (this may take a while)..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${DB_FILE}" "${BACKUP_DIR}/${DB_FILE}" || {
    echo -e "${RED}✗ Download failed!${NC}"
    exit 1
}
echo -e "${GREEN}✓ Downloaded: ${DB_FILE} ($(du -h ${BACKUP_DIR}/${DB_FILE} | cut -f1))${NC}"

if [ -n "$FILESTORE_FILE" ]; then
    echo ""
    echo "Downloading filestore..."
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${FILESTORE_FILE}" "${BACKUP_DIR}/${FILESTORE_FILE}" 2>/dev/null && {
        FILESTORE_SIZE=$(du -h "${BACKUP_DIR}/${FILESTORE_FILE}" | cut -f1)
        if [ "$FILESTORE_SIZE" != "0" ] && [ "$FILESTORE_SIZE" != "87" ]; then
            echo -e "${GREEN}✓ Downloaded: ${FILESTORE_FILE} (${FILESTORE_SIZE})${NC}"
        else
            echo -e "${YELLOW}⚠ Filestore file appears empty${NC}"
        fi
    } || echo -e "${YELLOW}⚠ Filestore download skipped${NC}"
fi

if [ -n "$ADDONS_FILE" ]; then
    echo ""
    echo "Downloading addons..."
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${ADDONS_FILE}" "${BACKUP_DIR}/${ADDONS_FILE}" 2>/dev/null && {
        echo -e "${GREEN}✓ Downloaded: ${ADDONS_FILE} ($(du -h ${BACKUP_DIR}/${ADDONS_FILE} | cut -f1))${NC}"
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

# Restore SQL file
echo "Importing SQL file..."
cat "${DB_FILE_PATH}" | docker-compose exec -T db psql -U odoo -d odoo 2>&1 | grep -v "NOTICE\|WARNING\|already exists" | tail -30 || {
    echo -e "${YELLOW}⚠ Some errors during restore (checking if successful)${NC}"
}

# Verify restore
echo "Verifying restore..."
RECORD_COUNT=$(docker-compose exec -T db psql -U odoo -d odoo -t -c "SELECT COUNT(*) FROM res_users;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$RECORD_COUNT" != "0" ] && [ -n "$RECORD_COUNT" ]; then
    echo -e "${GREEN}✓ Database restored successfully (${RECORD_COUNT} users found)${NC}"
else
    echo -e "${YELLOW}⚠ Database restore completed, verification unclear${NC}"
fi

# Restore filestore
if [ -n "$FILESTORE_FILE" ] && [ -f "${BACKUP_DIR}/${FILESTORE_FILE}" ]; then
    echo ""
    echo -e "${BLUE}Step 5: Restoring Filestore${NC}"
    
    FILESTORE_SIZE=$(stat -f%z "${BACKUP_DIR}/${FILESTORE_FILE}" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${FILESTORE_FILE}" 2>/dev/null || echo "0")
    if [ "$FILESTORE_SIZE" -gt 1000 ]; then
        echo "Extracting filestore..."
        mkdir -p ./var/filestore
        tar -xzf "${BACKUP_DIR}/${FILESTORE_FILE}" -C ./var/filestore/ 2>/dev/null && {
            echo -e "${GREEN}✓ Filestore extracted to ./var/filestore/${NC}"
        } || echo -e "${YELLOW}⚠ Filestore extraction had issues${NC}"
    else
        echo -e "${YELLOW}⚠ Filestore file appears empty, skipping${NC}"
    fi
fi

# Extract addons
if [ -n "$ADDONS_FILE" ] && [ -f "${BACKUP_DIR}/${ADDONS_FILE}" ]; then
    echo ""
    echo -e "${BLUE}Step 6: Extracting Addons${NC}"
    
    echo "Extracting addons..."
    mkdir -p ./addons/remote
    tar -xzf "${BACKUP_DIR}/${ADDONS_FILE}" -C ./addons/remote/ 2>/dev/null && {
        echo -e "${GREEN}✓ Addons extracted to ./addons/remote/${NC}"
        echo "Note: Review and merge with existing addons if needed"
    } || echo -e "${YELLOW}⚠ Addons extraction had issues${NC}"
fi

# Start Odoo
echo ""
echo -e "${BLUE}Step 7: Starting Odoo${NC}"
docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Full Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Files downloaded:"
echo "  ✓ docker-compose.remote.yml"
[ -f "./odoo.remote.env" ] && echo "  ✓ odoo.remote.env"
echo "  ✓ ${BACKUP_DIR}/${DB_FILE}"
[ -n "$FILESTORE_FILE" ] && echo "  ✓ ${BACKUP_DIR}/${FILESTORE_FILE}"
[ -n "$ADDONS_FILE" ] && echo "  ✓ ${BACKUP_DIR}/${ADDONS_FILE}"
echo ""
echo "Next steps:"
echo "1. Review docker-compose.remote.yml and merge with local if needed"
echo "2. Review odoo.remote.env and update local config if needed"
echo "3. Wait for Odoo to start (30-60 seconds)"
echo "4. Check logs: docker-compose logs odoo --tail=50"
echo "5. Access Odoo: http://localhost:8069"
echo "6. Login with your remote database credentials"
echo "7. Update modules: python3 upgrade_module.py"
echo ""

