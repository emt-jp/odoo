#!/bin/bash
# Interactive script to migrate database from od.emoment.tech to Docker
# This script will SSH to remote, export database, and import to Docker

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
    source .migration_config
fi

REMOTE_HOST="${REMOTE_HOST:-od.emoment.tech}"

echo "=========================================="
echo "Database Migration: ${REMOTE_HOST} → Docker"
echo "=========================================="
echo ""

# Get SSH credentials
echo -e "${BLUE}Step 1: SSH Connection Setup${NC}"
if [ -z "$REMOTE_SSH_USER" ]; then
    read -p "SSH Username for ${REMOTE_HOST}: " REMOTE_USER
else
    REMOTE_USER="$REMOTE_SSH_USER"
    echo "Using SSH user from config: ${REMOTE_USER}"
fi

echo ""
if [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    echo "Using SSH key from config: ${REMOTE_SSH_KEY}"
    SSH_KEY="$REMOTE_SSH_KEY"
    chmod 600 "$SSH_KEY" 2>/dev/null || true
    SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no"
    SCP_CMD="scp -i ${SSH_KEY} -o StrictHostKeyChecking=no"
else
    echo "SSH Authentication Method:"
    echo "1) SSH Key (recommended)"
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
        echo "Using password authentication"
        SSH_CMD="ssh -o StrictHostKeyChecking=no"
        SCP_CMD="scp -o StrictHostKeyChecking=no"
    fi
fi

# Test connection (skip for password auth as it requires interactive input)
if [ -n "$SSH_KEY" ]; then
    echo ""
    echo -e "${YELLOW}Testing SSH connection...${NC}"
    if ! $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "echo 'Connected'" > /dev/null 2>&1; then
        echo -e "${RED}✗ SSH connection failed!${NC}"
        echo "Please check your credentials and try again."
        exit 1
    fi
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo ""
    echo -e "${YELLOW}Note: SSH connection will be tested during Odoo detection (password will be prompted)${NC}"
fi

# Detect Odoo installation
echo ""
echo -e "${BLUE}Step 2: Detecting Odoo Installation${NC}"
echo "Searching for Odoo installation..."

ODOO_PATH=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in /opt/odoo /home/odoo /var/lib/odoo /home/\$(whoami)/odoo ~/ws/odoo /home/\$(whoami)/ws/odoo; do
        if [ -d \"\$path\" ] && [ -f \"\$path/odoo-bin\" ]; then
            echo \"\$path\"
            exit 0
        fi
    done
    find /opt /home /var ~/ws -name 'odoo-bin' -type f 2>/dev/null | head -1 | xargs dirname 2>/dev/null || echo ''
" | head -1)

# Check if it's a Docker installation
IS_DOCKER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ~/ws/odoo 2>/dev/null && test -f docker-compose.yml && docker ps --format '{{.Names}}' | grep -q odoo && echo 'yes' || echo 'no'" 2>/dev/null | head -1)

if [ "$IS_DOCKER" == "yes" ]; then
    echo -e "${GREEN}✓ Detected Docker-based Odoo installation${NC}"
    ODOO_PATH="~/ws/odoo"
    DOCKER_MODE=true
else
    if [ -z "$ODOO_PATH" ]; then
        echo -e "${YELLOW}⚠ Could not auto-detect Odoo path${NC}"
        read -p "Enter Odoo installation path: " ODOO_PATH
    else
        echo -e "${GREEN}✓ Found Odoo at: ${ODOO_PATH}${NC}"
    fi
    DOCKER_MODE=false
fi

# Find config files (odoo.conf, docker-compose.yml, .env)
echo ""
echo -e "${BLUE}Step 3: Reading Database Configuration${NC}"

# Try to find docker-compose.yml or .env files first
DOCKER_COMPOSE_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in ${ODOO_PATH} ${ODOO_PATH}/.. ${ODOO_PATH}/../.. ~/ws/odoo ~/odoo /opt/odoo; do
        if [ -f \"\$path/docker-compose.yml\" ]; then
            echo \"\$path/docker-compose.yml\"
            exit 0
        fi
    done
    find ${ODOO_PATH} ${ODOO_PATH}/.. ${ODOO_PATH}/../.. ~/ws/odoo ~/odoo -name 'docker-compose.yml' 2>/dev/null | head -1
" | head -1)

ENV_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in ${ODOO_PATH} ${ODOO_PATH}/.. ${ODOO_PATH}/../.. ~/ws/odoo ~/odoo /opt/odoo; do
        if [ -f \"\$path/.env\" ]; then
            echo \"\$path/.env\"
            exit 0
        fi
        if [ -f \"\$path/odoo.env\" ]; then
            echo \"\$path/odoo.env\"
            exit 0
        fi
    done
    find ${ODOO_PATH} ${ODOO_PATH}/.. ${ODOO_PATH}/../.. ~/ws/odoo ~/odoo -name '.env' -o -name 'odoo.env' 2>/dev/null | head -1
" | head -1)

CONFIG_FILE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    find ${ODOO_PATH} -name 'odoo.conf' -o -name 'openerp-server.conf' 2>/dev/null | head -1 || echo '${ODOO_PATH}/odoo.conf'
" | head -1)

# Read database password from .env or docker-compose.yml first
DB_PASSWORD=""
if [ -n "$ENV_FILE" ]; then
    echo -e "${GREEN}✓ Found env file: ${ENV_FILE}${NC}"
    DB_PASSWORD=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
        if [ -f '${ENV_FILE}' ]; then
            grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD|PASSWORD|DATABASE_PASSWORD)=' '${ENV_FILE}' 2>/dev/null | cut -d'=' -f2 | tr -d ' \"' | head -1
        fi
    " | head -1)
    
    # Also get DB_USER from env file if Docker mode
    if [ "$DOCKER_MODE" == "true" ]; then
        ENV_DB_USER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
            if [ -f '${ENV_FILE}' ]; then
                grep -E '^POSTGRES_USER=' '${ENV_FILE}' 2>/dev/null | cut -d'=' -f2 | tr -d ' \"' | head -1
            fi
        " | head -1)
        if [ -n "$ENV_DB_USER" ]; then
            DB_USER="$ENV_DB_USER"
            echo -e "${GREEN}✓ Using database user from env: ${DB_USER}${NC}"
        fi
    fi
fi

# If not found in .env, try docker-compose.yml
if [ -z "$DB_PASSWORD" ] && [ -n "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${GREEN}✓ Found docker-compose.yml: ${DOCKER_COMPOSE_FILE}${NC}"
    DB_PASSWORD=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
        if [ -f '${DOCKER_COMPOSE_FILE}' ]; then
            # Try environment section first
            grep -A 20 'environment:' '${DOCKER_COMPOSE_FILE}' 2>/dev/null | grep -E 'POSTGRES_PASSWORD|PASSWORD' | head -1 | sed 's/.*POSTGRES_PASSWORD[=: ]*\([^ ]*\).*/\1/' | tr -d ' \"' | head -1
            # If not found, try direct POSTGRES_PASSWORD line
            if [ -z \"\$DB_PASS\" ]; then
                grep 'POSTGRES_PASSWORD' '${DOCKER_COMPOSE_FILE}' 2>/dev/null | head -1 | sed 's/.*POSTGRES_PASSWORD[=: ]*\([^ ]*\).*/\1/' | tr -d ' \"' | head -1
            fi
        fi
    " | head -1)
fi

# Read database configuration from odoo.conf
DB_CONFIG=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    if [ -f '${CONFIG_FILE}' ]; then
        grep -E '^(db_name|db_user|db_host|db_port|db_password)=' '${CONFIG_FILE}' 2>/dev/null || echo ''
    fi
")

# Read from odoo.conf only if not already set from env files
if [ -z "$DB_NAME" ]; then
    DB_NAME=$(echo "$DB_CONFIG" | grep "^db_name" | cut -d'=' -f2 | tr -d ' ' || echo "odoo")
fi
if [ -z "$DB_USER" ]; then
    DB_USER=$(echo "$DB_CONFIG" | grep "^db_user" | cut -d'=' -f2 | tr -d ' ' || echo "odoo")
fi
if [ -z "$DB_HOST" ]; then
    DB_HOST=$(echo "$DB_CONFIG" | grep "^db_host" | cut -d'=' -f2 | tr -d ' ' || echo "localhost")
fi
DB_PORT=$(echo "$DB_CONFIG" | grep "^db_port" | cut -d'=' -f2 | tr -d ' ' || echo "5432")

# If password not found in .env/docker-compose, try odoo.conf
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(echo "$DB_CONFIG" | grep "^db_password" | cut -d'=' -f2 | tr -d ' ' || echo "")
fi

# For Docker installations, detect actual Odoo database name and user
if [ "$DOCKER_MODE" == "true" ]; then
    PSQL_CONTAINER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ~/ws/odoo && docker ps --format '{{.Names}}' | grep -E '^odoo.*psql|^odoo.*postgres|^odoo.*db' | head -1" 2>/dev/null | head -1)
    if [ -z "$PSQL_CONTAINER" ]; then
        PSQL_CONTAINER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ~/ws/odoo && docker ps --format '{{.Names}}' | grep -E 'psql|postgres|db' | head -1" 2>/dev/null | head -1)
    fi
    if [ -n "$PSQL_CONTAINER" ]; then
        # Detect database name
        if [ -z "$DB_NAME" ] || [ "$DB_NAME" == "odoo" ] || [ "$DB_NAME" == "postgres" ]; then
            DETECTED_DB=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "docker exec ${PSQL_CONTAINER} psql -U ${DB_USER:-odoo18} -d postgres -t -c \"SELECT datname FROM pg_database WHERE datname LIKE 'odoo%' ORDER BY datname LIMIT 1;\" 2>/dev/null" | tr -d ' \n\r' | head -1)
            if [ -n "$DETECTED_DB" ] && [ "$DETECTED_DB" != "postgres" ]; then
                DB_NAME="$DETECTED_DB"
                echo -e "${GREEN}✓ Detected Odoo database: ${DB_NAME}${NC}"
            fi
        fi
    fi
fi

# Clean up values
DB_NAME=$(echo "$DB_NAME" | grep -v "^False$" | head -1 || echo "odoo")
DB_USER=$(echo "$DB_USER" | grep -v "^False$" | head -1 || echo "odoo")
DB_HOST=$(echo "$DB_HOST" | grep -v "^False$" | head -1 || echo "localhost")
DB_PASSWORD=$(echo "$DB_PASSWORD" | grep -v "^False$" | head -1 || echo "")

# Ensure we have the correct user for Docker installations (fallback check)
if [ "$DOCKER_MODE" == "true" ] && [ "$DB_USER" == "odoo" ]; then
    # Try to get from env file if not already set
    if [ -z "$ENV_DB_USER" ] && [ -n "$ENV_FILE" ]; then
        ENV_DB_USER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
            if [ -f '${ENV_FILE}' ]; then
                grep -E '^POSTGRES_USER=' '${ENV_FILE}' 2>/dev/null | cut -d'=' -f2 | tr -d ' \"' | head -1
            fi
        " | head -1)
    fi
    if [ -n "$ENV_DB_USER" ]; then
        DB_USER="$ENV_DB_USER"
        echo -e "${GREEN}✓ Using database user from env: ${DB_USER}${NC}"
    fi
fi

if [ -z "$DB_NAME" ]; then DB_NAME="odoo"; fi
if [ -z "$DB_USER" ]; then DB_USER="odoo"; fi
if [ -z "$DB_HOST" ]; then DB_HOST="localhost"; fi

echo -e "${GREEN}✓ Database: ${DB_NAME}"
echo -e "✓ User: ${DB_USER}"
echo -e "✓ Host: ${DB_HOST}:${DB_PORT}${NC}"

# Get password if still not found
if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" == "False" ]; then
    echo ""
    echo -e "${YELLOW}⚠ Database password not found in config files${NC}"
    read -sp "Database password for ${DB_USER}: " DB_PASSWORD
    echo ""
else
    echo -e "${GREEN}✓ Password found in remote config${NC}"
fi

# Create backup on remote
echo ""
echo -e "${BLUE}Step 4: Creating Database Backup${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REMOTE_BACKUP="/tmp/odoo_backup_${TIMESTAMP}.dump"

echo "Creating backup on remote server..."

BACKUP_SUCCESS=false

# Handle Docker installation
if [ "$DOCKER_MODE" == "true" ]; then
    echo "Using Docker pg_dump..."
    # Get PostgreSQL container name - look for odoo-specific containers first
    PSQL_CONTAINER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ~/ws/odoo && docker ps --format '{{.Names}}' | grep -E '^odoo.*psql|^odoo.*postgres|^odoo.*db' | head -1" 2>/dev/null | head -1)
    # Fallback to any psql/postgres/db container if odoo-specific not found
    if [ -z "$PSQL_CONTAINER" ]; then
        PSQL_CONTAINER=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ~/ws/odoo && docker ps --format '{{.Names}}' | grep -E 'psql|postgres|db' | head -1" 2>/dev/null | head -1)
    fi
    
    if [ -z "$PSQL_CONTAINER" ]; then
        echo -e "${RED}✗ Could not find PostgreSQL container${NC}"
        exit 1
    fi
    
    echo "Found PostgreSQL container: ${PSQL_CONTAINER}"
    
    # Use docker exec to create backup
    if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "docker exec ${PSQL_CONTAINER} pg_dump -U ${DB_USER} -d ${DB_NAME} -F c -f /tmp/odoo_backup_${TIMESTAMP}.dump" > /dev/null 2>&1; then
        # Copy backup from container to host
        $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "docker cp ${PSQL_CONTAINER}:/tmp/odoo_backup_${TIMESTAMP}.dump ${REMOTE_BACKUP}" > /dev/null 2>&1
        BACKUP_SUCCESS=true
        echo -e "${GREEN}✓ Backup created using Docker pg_dump${NC}"
    else
        echo -e "${RED}✗ Docker backup failed!${NC}"
        echo "Trying alternative method..."
        # Alternative: use pg_dump from host connecting to container
        if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "PGPASSWORD='${DB_PASSWORD}' pg_dump -h localhost -p 5432 -U ${DB_USER} -d ${DB_NAME} -F c -f ${REMOTE_BACKUP}" > /dev/null 2>&1; then
            BACKUP_SUCCESS=true
            echo -e "${GREEN}✓ Backup created using pg_dump from host${NC}"
        fi
    fi
else
    # Try Odoo CLI backup first
    if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${ODOO_PATH} && test -f odoo-bin" 2>/dev/null; then
        echo "Attempting Odoo CLI backup..."
        if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${ODOO_PATH} && python3 odoo-bin -c ${CONFIG_FILE} -d ${DB_NAME} --backup=${REMOTE_BACKUP} --stop-after-init" > /dev/null 2>&1; then
            BACKUP_SUCCESS=true
            echo -e "${GREEN}✓ Backup created using Odoo CLI${NC}"
        fi
    fi
    
    # Fallback to pg_dump
    if [ "$BACKUP_SUCCESS" = false ]; then
        echo "Using pg_dump..."
        if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "PGPASSWORD='${DB_PASSWORD}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -F c -f ${REMOTE_BACKUP}" > /dev/null 2>&1; then
            BACKUP_SUCCESS=true
            echo -e "${GREEN}✓ Backup created using pg_dump${NC}"
        fi
    fi
fi

if [ "$BACKUP_SUCCESS" = false ]; then
    echo -e "${RED}✗ Backup failed!${NC}"
    echo "Please check database credentials and permissions."
    exit 1
fi

# Check backup file exists
if ! $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "test -f ${REMOTE_BACKUP}" 2>/dev/null; then
    echo -e "${RED}✗ Backup file not found!${NC}"
    exit 1
fi

BACKUP_SIZE=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "du -h ${REMOTE_BACKUP} | cut -f1")
echo -e "${GREEN}✓ Backup size: ${BACKUP_SIZE}${NC}"

# Download backup
echo ""
echo -e "${BLUE}Step 5: Downloading Backup${NC}"
LOCAL_BACKUP="${BACKUP_DIR}/odoo_backup_${TIMESTAMP}.dump"

echo "Downloading ${REMOTE_BACKUP}..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BACKUP}" "${LOCAL_BACKUP}" || {
    echo -e "${RED}✗ Download failed!${NC}"
    exit 1
}

echo -e "${GREEN}✓ Backup downloaded: ${LOCAL_BACKUP}${NC}"

# Cleanup remote
echo "Cleaning up remote backup..."
$SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "rm -f ${REMOTE_BACKUP}"

# Restore to Docker
echo ""
echo -e "${BLUE}Step 6: Restoring to Docker${NC}"

echo "Stopping Odoo container..."
docker-compose stop odoo 2>/dev/null || true
sleep 2

echo "Recreating database..."
docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;" 2>/dev/null || true
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;" 2>/dev/null || true

echo "Restoring backup (this may take a few minutes)..."
cat "${LOCAL_BACKUP}" | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl -v 2>&1 | tail -20 || {
    echo -e "${YELLOW}⚠ Some warnings during restore (may be normal)${NC}"
}

echo -e "${GREEN}✓ Database restored${NC}"

# Start Odoo
echo "Starting Odoo container..."
docker-compose start odoo

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Backup saved: ${LOCAL_BACKUP}"
echo ""
echo "Next steps:"
echo "1. Wait for Odoo to start (30-60 seconds)"
echo "2. Check logs: docker-compose logs odoo --tail=50"
echo "3. Access Odoo: http://localhost:8069"
echo "4. Login with your remote database credentials"
echo "5. Update modules if needed: python3 upgrade_module.py"
echo ""

