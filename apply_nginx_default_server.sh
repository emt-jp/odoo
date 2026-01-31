#!/bin/bash
# Apply default_server fix to nginx config

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

echo "Applying default_server fix..."
cp /home/as/ws/odoo/ops/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf

echo "Testing configuration..."
if nginx -t; then
    echo "✓ Configuration is valid"
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded"
else
    echo "✗ Configuration test failed!"
    exit 1
fi

echo ""
echo "✅ Fix applied successfully!"

