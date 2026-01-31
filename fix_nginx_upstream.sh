#!/bin/bash
# Fix nginx by using upstream blocks instead of variables
# Run with: sudo ./fix_nginx_upstream.sh

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

echo "=========================================="
echo "Fixing Nginx with Upstream Blocks"
echo "=========================================="
echo ""

BACKUP="/etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/conf.d/nginx.conf "$BACKUP"
echo "✓ Backed up to: $BACKUP"

echo "Applying upstream block configuration..."
cp /home/as/ws/odoo/ops/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf

echo "Testing configuration..."
if nginx -t; then
    echo "✓ Configuration is valid"
    echo ""
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "Testing connection..."
    sleep 1
    RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1)
    echo "Response code: $RESPONSE"
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "303" ] || [ "$RESPONSE" = "302" ]; then
        echo "✓ SUCCESS! Nginx is now working correctly"
    else
        echo "⚠ Still getting $RESPONSE"
        echo "Check error logs: sudo tail -30 /var/log/nginx/error.log"
    fi
else
    echo "✗ Configuration test failed!"
    echo "Restoring backup..."
    cp "$BACKUP" /etc/nginx/conf.d/nginx.conf
    exit 1
fi

echo ""
echo "=========================================="
echo "Fix Complete"
echo "=========================================="

