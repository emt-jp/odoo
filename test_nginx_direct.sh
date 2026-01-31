#!/bin/bash
# Test nginx with direct proxy_pass (no upstream)
# Run with: sudo ./test_nginx_direct.sh

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

CONF="/etc/nginx/conf.d/nginx.conf"
BACKUP="/etc/nginx/conf.d/nginx.conf.test_direct"

echo "Testing with direct proxy_pass (no upstream block)..."
cp "$CONF" "$BACKUP"

# Replace upstream with direct proxy_pass
sed -i 's|proxy_pass http://odoo_backend;|proxy_pass http://127.0.0.1:8069;|' "$CONF"

if nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Config test passed"
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    
    sleep 1
    RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1)
    echo "Response code: $RESPONSE"
    
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "303" ] || [ "$RESPONSE" = "302" ]; then
        echo "✓ SUCCESS with direct proxy_pass!"
        echo "The issue is with upstream block resolution"
    else
        echo "✗ Still getting $RESPONSE"
        echo "The issue is not with upstream blocks"
    fi
else
    echo "✗ Config test failed"
fi

# Restore
cp "$BACKUP" "$CONF"
nginx -t > /dev/null 2>&1 && systemctl reload nginx > /dev/null 2>&1
echo "✓ Config restored"

