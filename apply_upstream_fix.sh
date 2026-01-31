#!/bin/bash
# Apply upstream block fix
# Run with: sudo ./apply_upstream_fix.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Applying Upstream Block Fix"
echo "=========================================="
echo ""

# Copy config
cp "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/od_emoment_tech.conf

# Test
if nginx -t; then
    echo "✓ Config valid"
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "Testing..."
    sleep 1
    curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
    echo ""
    echo "Check logs:"
    echo "  sudo tail -5 /var/log/nginx/od_emoment_tech_access.log"
else
    echo "✗ Config invalid!"
    exit 1
fi

