#!/bin/bash
# Copy nginx config and SSL certificates from remote
# Remote: as@103.101.59.102 (uses SSH keys)

set -e

REMOTE_HOST="103.101.59.102"
REMOTE_USER="as"
NGINX_CONFIG_DIR="./ops/nginx"
SSL_CERTS_DIR="./ops/ssl"

# Create directories
mkdir -p "${NGINX_CONFIG_DIR}/conf.d"
mkdir -p "${NGINX_CONFIG_DIR}/sites-available"
mkdir -p "${SSL_CERTS_DIR}"

SSH_OPTS="-o StrictHostKeyChecking=no"

echo "=========================================="
echo "Copying Nginx Config & SSL Certificates"
echo "From: ${REMOTE_USER}@${REMOTE_HOST}"
echo "=========================================="
echo ""

# Step 1: Find nginx config location
echo "Step 1: Finding Nginx configuration..."
NGINX_PATH=$(ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "
    for path in /etc/nginx /usr/local/nginx/conf /usr/local/etc/nginx; do
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

if [ -z "$NGINX_PATH" ]; then
    echo "⚠ Could not auto-detect Nginx config path, using default: /etc/nginx"
    NGINX_PATH="/etc/nginx"
else
    echo "✓ Found Nginx config at: ${NGINX_PATH}"
fi

# Copy nginx configuration
echo ""
echo "Copying Nginx configuration files..."
scp ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/nginx.conf" "${NGINX_CONFIG_DIR}/nginx.conf" 2>/dev/null && echo "✓ Copied nginx.conf" || echo "⚠ Could not copy nginx.conf"

if ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_PATH}/conf.d" 2>/dev/null; then
    scp ${SSH_OPTS} -r "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/conf.d/"* "${NGINX_CONFIG_DIR}/conf.d/" 2>/dev/null && echo "✓ Copied conf.d files" || echo "⚠ Could not copy conf.d files"
fi

if ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${NGINX_PATH}/sites-available" 2>/dev/null; then
    scp ${SSH_OPTS} -r "${REMOTE_USER}@${REMOTE_HOST}:${NGINX_PATH}/sites-available/"* "${NGINX_CONFIG_DIR}/sites-available/" 2>/dev/null && echo "✓ Copied sites-available files" || echo "⚠ Could not copy sites-available files"
fi

# Step 2: Find SSL certificates
echo ""
echo "Step 2: Finding SSL certificates..."
SSL_PATHS=$(ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "
    # Try common SSL certificate locations
    for path in /etc/letsencrypt/live /etc/ssl/certs /etc/nginx/ssl /root/ssl ~/ssl; do
        if [ -d \"\$path\" ]; then
            echo \"\$path\"
        fi
    done
    # Also check nginx config for cert paths
    if [ -f ${NGINX_PATH}/nginx.conf ] || [ -f ${NGINX_PATH}/sites-available/* ] 2>/dev/null; then
        grep -h 'ssl_certificate' ${NGINX_PATH}/*.conf ${NGINX_PATH}/sites-available/* ${NGINX_PATH}/conf.d/* 2>/dev/null | \
        grep -v '^#' | sed 's/.*ssl_certificate[^/]*//' | sed 's/;.*//' | xargs dirname 2>/dev/null | sort -u | head -3
    fi
" 2>/dev/null)

if [ -z "$SSL_PATHS" ]; then
    echo "⚠ Could not auto-detect SSL certificate path, trying common locations..."
    # Try common paths directly
    for test_path in /etc/letsencrypt/live /etc/nginx/ssl /etc/ssl/certs; do
        if ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${test_path}" 2>/dev/null; then
            SSL_PATH="$test_path"
            echo "✓ Found SSL certificates at: ${SSL_PATH}"
            break
        fi
    done
else
    echo "✓ Found SSL certificate paths:"
    echo "$SSL_PATHS" | while read -r path; do
        echo "  - $path"
    done
    SSL_PATH=$(echo "$SSL_PATHS" | head -1)
fi

# Copy SSL certificates
if [ -n "$SSL_PATH" ]; then
    echo ""
    echo "Copying SSL certificates from ${SSL_PATH}..."
    
    # Check if it's Let's Encrypt (has domain subdirectories)
    if ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "test -d ${SSL_PATH} && ls -d ${SSL_PATH}/*/ 2>/dev/null | head -1" >/dev/null 2>&1; then
        echo "Detected Let's Encrypt structure (domain directories)..."
        ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" "ls -d ${SSL_PATH}/*/" 2>/dev/null | while read -r domain_dir; do
            if [ -n "$domain_dir" ]; then
                DOMAIN=$(basename "$domain_dir")
                echo "  Copying certificates for domain: ${DOMAIN}"
                mkdir -p "${SSL_CERTS_DIR}/${DOMAIN}"
                scp ${SSH_OPTS} -r "${REMOTE_USER}@${REMOTE_HOST}:${domain_dir}"* "${SSL_CERTS_DIR}/${DOMAIN}/" 2>/dev/null && echo "    ✓ Copied ${DOMAIN}" || echo "    ⚠ Failed to copy ${DOMAIN}"
            fi
        done
    else
        echo "Copying all certificate files..."
        scp ${SSH_OPTS} -r "${REMOTE_USER}@${REMOTE_HOST}:${SSL_PATH}/"* "${SSL_CERTS_DIR}/" 2>/dev/null && echo "✓ Copied SSL certificates" || echo "⚠ Could not copy SSL certificates"
    fi
else
    echo "⚠ Skipping SSL certificate copy (no path found)"
fi

echo ""
echo "=========================================="
echo "✅ Copy Complete!"
echo "=========================================="
echo ""
echo "Files copied to:"
echo "  Nginx config: ${NGINX_CONFIG_DIR}/"
ls -lh "${NGINX_CONFIG_DIR}"/*.conf 2>/dev/null | awk '{print "    - " $9}' || true
find "${NGINX_CONFIG_DIR}/conf.d" -name "*.conf" 2>/dev/null | head -5 | awk '{print "    - " $1}' || true
echo ""
if [ -d "${SSL_CERTS_DIR}" ] && [ "$(ls -A ${SSL_CERTS_DIR} 2>/dev/null)" ]; then
    echo "  SSL certificates: ${SSL_CERTS_DIR}/"
    find "${SSL_CERTS_DIR}" -type f | head -10 | awk '{print "    - " $1}' || true
fi
echo ""
echo "Next: Review and configure the files as needed"

