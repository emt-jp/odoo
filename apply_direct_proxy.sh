#!/bin/bash
# Apply direct proxy_pass configuration
# Run with: sudo ./apply_direct_proxy.sh

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

echo "Applying direct proxy_pass configuration..."
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
        echo ""
        echo "✓✓✓ SUCCESS! Nginx is now working correctly!"
        echo "The issue was with upstream block resolution."
    else
        echo ""
        echo "⚠ Still getting $RESPONSE"
        echo "The issue is not with upstream blocks - need to investigate further"
        echo "Check: sudo tail -30 /var/log/nginx/error.log"
    fi
else
    echo "✗ Configuration test failed!"
    exit 1
fi

