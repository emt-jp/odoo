#!/bin/bash
# Automated download of Nginx config and SSL certificates
# Tries common locations automatically

set -e

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
NGINX_CONFIG_DIR="./ops/nginx"
SSL_CERTS_DIR="./ops/ssl"
mkdir -p "${NGINX_CONFIG_DIR}"
mkdir -p "${SSL_CERTS_DIR}"

SSH_CMD="ssh -o StrictHostKeyChecking=no"
SCP_CMD="scp -o StrictHostKeyChecking=no -r"

echo "Downloading Nginx config and SSL certificates..."
echo "You will be prompted for SSH password"
echo ""

# Find and download nginx config
echo "Searching for Nginx configuration..."
NGINX_PATHS=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in /etc/nginx /usr/local/nginx/conf /usr/local/etc/nginx; do
        if [ -d \"\$path\" ]; then
            echo \"\$path\"
        fi
    done
" 2>/dev/null)

if [ -n "$NGINX_PATHS" ]; then
    NGINX_PATH=$(echo "$NGINX_PATHS" | head -1)
    echo "Found Nginx at: $NGINX_PATH"
    
    # Download main config
    $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/nginx.conf" "${NGINX_CONFIG_DIR}/" 2>/dev/null || true
    
    # Download sites-available
    if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_PATH}/sites-available" 2>/dev/null; then
        mkdir -p "${NGINX_CONFIG_DIR}/sites-available"
        $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/sites-available/*" "${NGINX_CONFIG_DIR}/sites-available/" 2>/dev/null || true
    fi
    
    # Download conf.d
    if $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_PATH}/conf.d" 2>/dev/null; then
        mkdir -p "${NGINX_CONFIG_DIR}/conf.d"
        $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/conf.d/*" "${NGINX_CONFIG_DIR}/conf.d/" 2>/dev/null || true
    fi
    
    echo "✓ Nginx config downloaded"
else
    echo "⚠ Nginx config not found in standard locations"
fi

# Find and download SSL certificates
echo ""
echo "Searching for SSL certificates..."
SSL_PATHS=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in /etc/letsencrypt/live /etc/ssl/certs /etc/nginx/ssl /root/ssl ~/ssl; do
        if [ -d \"\$path\" ]; then
            echo \"\$path\"
        fi
    done
" 2>/dev/null)

if [ -n "$SSL_PATHS" ]; then
    SSL_PATH=$(echo "$SSL_PATHS" | head -1)
    echo "Found SSL certificates at: $SSL_PATH"
    
    # If Let's Encrypt, download domain directories
    if echo "$SSL_PATH" | grep -q "letsencrypt"; then
        $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "ls -d ${SSL_PATH}/*/ 2>/dev/null" | while read domain_dir; do
            if [ -n "$domain_dir" ]; then
                DOMAIN=$(basename "$domain_dir")
                mkdir -p "${SSL_CERTS_DIR}/${DOMAIN}"
                $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${domain_dir}*" "${SSL_CERTS_DIR}/${DOMAIN}/" 2>/dev/null || true
                echo "✓ Downloaded certificates for $DOMAIN"
            fi
        done
    else
        $SCP_CMD "${REMOTE_USER}@${REMOTE_HOST}:${SSL_PATH}/*" "${SSL_CERTS_DIR}/" 2>/dev/null || true
        echo "✓ SSL certificates downloaded"
    fi
else
    echo "⚠ SSL certificates not found in standard locations"
fi

# Extract hostname from config
echo ""
echo "Hostnames found in config:"
grep -h "server_name" "${NGINX_CONFIG_DIR}"/*.conf "${NGINX_CONFIG_DIR}/sites-available/"* "${NGINX_CONFIG_DIR}/conf.d/"* 2>/dev/null | \
    grep -v "^#" | sed 's/server_name//' | tr ';' '\n' | tr ' ' '\n' | grep -v '^$' | grep -v '^_' | sort -u

echo ""
echo "✅ Download complete!"
echo "Files in: ${NGINX_CONFIG_DIR}/ and ${SSL_CERTS_DIR}/"

