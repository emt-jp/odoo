#!/bin/bash
# Apply cleaned up nginx config (removed emoment.tech, rm.emoment.tech, mm.emoment.tech)

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

echo "Applying cleaned up nginx configuration..."
cp /home/as/ws/odoo/ops/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf

echo "Testing configuration..."
if nginx -t; then
    echo "✓ Configuration is valid"
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded successfully"
    echo ""
    echo "Removed domains: emoment.tech, rm.emoment.tech, mm.emoment.tech"
    echo "Kept domain: od.emoment.tech"
else
    echo "✗ Configuration test failed!"
    exit 1
fi

