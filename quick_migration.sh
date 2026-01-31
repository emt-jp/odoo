#!/bin/bash
# Quick migration - tries to connect and download everything
# Usage: REMOTE_SSH_KEY=/path/to/key ./quick_migration.sh

set -e

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
REMOTE_PATH="~/ws/odoo"
BACKUP_DIR="./var/backups"
mkdir -p "${BACKUP_DIR}"

# Use SSH key if provided
if [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    SSH_CMD="ssh -i ${REMOTE_SSH_KEY} -o StrictHostKeyChecking=no -o BatchMode=yes"
    SCP_CMD="scp -i ${REMOTE_SSH_KEY} -o StrictHostKeyChecking=no -o BatchMode=yes"
else
    SSH_CMD="ssh -o StrictHostKeyChecking=no"
    SCP_CMD="scp -o StrictHostKeyChecking=no"
fi

echo "Downloading configuration files..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/docker-compose.yml" "./docker-compose.remote.yml"
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/odoo.env" "./odoo.remote.env" 2>/dev/null || echo "odoo.env not found"

echo "Finding backup directory..."
BACKUP_DIR_REMOTE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && ls -d _backup-* 2>/dev/null | head -1")
echo "Backup dir: ${BACKUP_DIR_REMOTE}"

DB_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *.sql 2>/dev/null | head -1")
FILESTORE_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *filestore*.tgz 2>/dev/null | head -1")
ADDONS_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH}/${BACKUP_DIR_REMOTE} && ls -1 *addons*.tgz 2>/dev/null | head -1")

echo "Downloading: ${DB_FILE}"
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${DB_FILE}" "${BACKUP_DIR}/"

[ -n "$FILESTORE_FILE" ] && $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${FILESTORE_FILE}" "${BACKUP_DIR}/" 2>/dev/null
[ -n "$ADDONS_FILE" ] && $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DIR_REMOTE}/${ADDONS_FILE}" "${BACKUP_DIR}/" 2>/dev/null

echo "Restoring database..."
docker-compose stop odoo 2>/dev/null || true
sleep 2
docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;" 2>/dev/null || true
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;" 2>/dev/null || true
cat "${BACKUP_DIR}/${DB_FILE}" | docker-compose exec -T db psql -U odoo -d odoo 2>&1 | tail -20

docker-compose start odoo
echo "✅ Migration complete!"

