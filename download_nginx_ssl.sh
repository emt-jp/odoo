#!/bin/bash
# Download Nginx config and SSL certificates from remote host
# From: 103.101.59.102 (as@emoment-tech)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
NGINX_CONFIG_DIR="./ops/nginx"
SSL_CERTS_DIR="./ops/ssl"
mkdir -p "${NGINX_CONFIG_DIR}"
mkdir -p "${SSL_CERTS_DIR}"

echo "=========================================="
echo "Download Nginx Config & SSL Certificates"
echo "From: ${REMOTE_USER}@${REMOTE_HOST}"
echo "=========================================="
echo ""

# SSH will prompt for password
SSH_CMD="ssh -o StrictHostKeyChecking=no"
SCP_CMD="scp -o StrictHostKeyChecking=no -r"

echo -e "${YELLOW}You will be prompted for SSH password for ${REMOTE_USER}@${REMOTE_HOST}${NC}"
echo ""

# Step 1: Find Nginx config location
echo -e "${BLUE}Step 1: Finding Nginx Configuration${NC}"

NGINX_CONF_PATH=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    # Try common nginx config locations
    for path in /etc/nginx /usr/local/nginx/conf /usr/local/etc/nginx ~/nginx /opt/nginx/conf; do
        if [ -d \"\$path\" ] && [ -f \"\$path/nginx.conf\" ]; then
            echo \"\$path\"
            exit 0
        fi
    done
    # Try to find nginx.conf
    nginx_conf=\$(find /etc /usr/local /opt -name 'nginx.conf' -type f 2>/dev/null | head -1)
    if [ -n \"\$nginx_conf\" ]; then
        dirname \"\$nginx_conf\"
    fi
" 2>/dev/null | head -1)

if [ -z "$NGINX_CONF_PATH" ]; then
    echo -e "${YELLOW}⚠ Could not auto-detect Nginx config path${NC}"
    read -p "Enter Nginx config directory path: " NGINX_CONF_PATH
else
    echo -e "${GREEN}✓ Found Nginx config at: ${NGINX_CONF_PATH}${NC}"
fi

# List nginx config files
echo ""
echo "Nginx configuration files:"
$SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "ls -lah ${NGINX_CONF_PATH}/*.conf ${NGINX_CONF_PATH}/sites-available/* ${NGINX_CONF_PATH}/conf.d/* 2>/dev/null | head -20"

# Step 2: Find SSL certificates
echo ""
echo -e "${BLUE}Step 2: Finding SSL Certificates${NC}"

SSL_PATHS=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    # Try common SSL certificate locations
    for path in /etc/ssl/certs /etc/letsencrypt/live /etc/nginx/ssl ~/ssl ~/certs; do
        if [ -d \"\$path\" ]; then
            echo \"\$path\"
        fi
    done
    # Also check nginx config for cert paths
    if [ -f ${NGINX_CONF_PATH}/nginx.conf ] || [ -f ${NGINX_CONF_PATH}/sites-available/* ]; then
        grep -h 'ssl_certificate' ${NGINX_CONF_PATH}/*.conf ${NGINX_CONF_PATH}/sites-available/* ${NGINX_CONF_PATH}/conf.d/* 2>/dev/null | \
        grep -v '^#' | sed 's/.*ssl_certificate[^/]*//' | sed 's/;.*//' | xargs dirname 2>/dev/null | sort -u | head -3
    fi
" 2>/dev/null)

if [ -z "$SSL_PATHS" ]; then
    echo -e "${YELLOW}⚠ Could not auto-detect SSL certificate path${NC}"
    read -p "Enter SSL certificate directory path (or press Enter to skip): " SSL_PATH
else
    echo -e "${GREEN}✓ Found SSL certificate paths:${NC}"
    echo "$SSL_PATHS" | while read path; do
        echo "  - $path"
    done
    SSL_PATH=$(echo "$SSL_PATHS" | head -1)
fi

# Step 3: Download Nginx config
echo ""
echo -e "${BLUE}Step 3: Downloading Nginx Configuration${NC}"

echo "Downloading main nginx.conf..."
$SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_CONF_PATH}/nginx.conf" "${NGINX_CONFIG_DIR}/nginx.conf" 2>/dev/null && {
    echo -e "${GREEN}✓ Downloaded nginx.conf${NC}"
} || echo -e "${YELLOW}⚠ nginx.conf not found or already exists${NC}"

# Download sites-available if exists
if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_CONF_PATH}/sites-available" 2>/dev/null; then
    echo "Downloading sites-available..."
    mkdir -p "${NGINX_CONFIG_DIR}/sites-available"
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_CONF_PATH}/sites-available/*" "${NGINX_CONFIG_DIR}/sites-available/" 2>/dev/null && {
        echo -e "${GREEN}✓ Downloaded sites-available configs${NC}"
    } || echo -e "${YELLOW}⚠ sites-available download had issues${NC}"
fi

# Download conf.d if exists
if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_CONF_PATH}/conf.d" 2>/dev/null; then
    echo "Downloading conf.d..."
    mkdir -p "${NGINX_CONFIG_DIR}/conf.d"
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_CONF_PATH}/conf.d/*" "${NGINX_CONFIG_DIR}/conf.d/" 2>/dev/null && {
        echo -e "${GREEN}✓ Downloaded conf.d configs${NC}"
    } || echo -e "${YELLOW}⚠ conf.d download had issues${NC}"
fi

# Download all .conf files from main directory
echo "Downloading additional config files..."
$SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "cd ${NGINX_CONF_PATH} && find . -maxdepth 1 -name '*.conf' -type f" 2>/dev/null | while read conf_file; do
    if [ -n "$conf_file" ]; then
        $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_CONF_PATH}/${conf_file}" "${NGINX_CONFIG_DIR}/" 2>/dev/null && {
            echo -e "${GREEN}✓ Downloaded $(basename ${conf_file})${NC}"
        }
    fi
done

# Step 4: Download SSL certificates
if [ -n "$SSL_PATH" ]; then
    echo ""
    echo -e "${BLUE}Step 4: Downloading SSL Certificates${NC}"
    echo -e "${YELLOW}You will be prompted for SSH password again${NC}"
    
    # List certificate files
    echo "Certificate files found:"
    $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "find ${SSL_PATH} -type f \\( -name '*.crt' -o -name '*.pem' -o -name '*.key' -o -name '*.cert' \\) 2>/dev/null | head -20"
    
    # Download certificates
    echo ""
    echo "Downloading SSL certificates..."
    
    # If it's a Let's Encrypt directory, download the live directory structure
    if echo "$SSL_PATH" | grep -q "letsencrypt"; then
        echo "Detected Let's Encrypt certificates..."
        $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "ls -d ${SSL_PATH}/*/ 2>/dev/null" | while read domain_dir; do
            if [ -n "$domain_dir" ]; then
                DOMAIN=$(basename "$domain_dir")
                echo "Downloading certificates for domain: ${DOMAIN}"
                mkdir -p "${SSL_CERTS_DIR}/${DOMAIN}"
                $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${domain_dir}*" "${SSL_CERTS_DIR}/${DOMAIN}/" 2>/dev/null && {
                    echo -e "${GREEN}✓ Downloaded certificates for ${DOMAIN}${NC}"
                } || echo -e "${YELLOW}⚠ Failed to download certificates for ${DOMAIN}${NC}"
            fi
        done
    else
        # Download all certificate files
        $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${SSL_PATH}/*" "${SSL_CERTS_DIR}/" 2>/dev/null && {
            echo -e "${GREEN}✓ Downloaded SSL certificates${NC}"
        } || echo -e "${YELLOW}⚠ SSL certificate download had issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Skipping SSL certificate download (path not found)${NC}"
fi

# Step 5: Extract hostname from nginx config
echo ""
echo -e "${BLUE}Step 5: Extracting Hostname Information${NC}"

if [ -f "${NGINX_CONFIG_DIR}/nginx.conf" ] || [ -f "${NGINX_CONFIG_DIR}/sites-available/"* ] 2>/dev/null; then
    echo "Hostnames found in Nginx config:"
    grep -h "server_name" "${NGINX_CONFIG_DIR}"/*.conf "${NGINX_CONFIG_DIR}/sites-available/"* "${NGINX_CONFIG_DIR}/conf.d/"* 2>/dev/null | \
        grep -v "^#" | sed 's/server_name//' | tr ';' '\n' | tr ' ' '\n' | grep -v '^$' | grep -v '^_' | sort -u | while read hostname; do
        echo "  - $hostname"
    done
fi

# Step 6: Create summary
echo ""
echo -e "${GREEN}=========================================="
echo "✅ Download Complete!"
echo "==========================================${NC}"
echo ""
echo "Files downloaded:"
echo "  Nginx config: ${NGINX_CONFIG_DIR}/"
ls -lh "${NGINX_CONFIG_DIR}"/*.conf 2>/dev/null | awk '{print "    - " $9}'
ls -lh "${NGINX_CONFIG_DIR}/sites-available/"*.conf 2>/dev/null 2>/dev/null | awk '{print "    - " $9}'
echo ""
if [ -d "${SSL_CERTS_DIR}" ] && [ "$(ls -A ${SSL_CERTS_DIR} 2>/dev/null)" ]; then
    echo "  SSL certificates: ${SSL_CERTS_DIR}/"
    find "${SSL_CERTS_DIR}" -type f | head -10 | awk '{print "    - " $1}'
    echo ""
fi

echo "Next steps:"
echo "1. Review Nginx configuration files"
echo "2. Update paths in nginx config if needed"
echo "3. Copy SSL certificates to appropriate location"
echo "4. Update docker-compose.yml if using nginx in Docker"
echo "5. Test nginx configuration: nginx -t"
echo ""

