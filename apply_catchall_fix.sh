#!/bin/bash
# Apply catch-all server_name fix
# Run with: sudo ./apply_catchall_fix.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Applying Catch-All Server Name Fix"
echo "=========================================="
echo ""

cp "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/od_emoment_tech.conf

if nginx -t 2>&1; then
    echo "✓ Config valid"
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "Testing..."
    sleep 1
    curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
    echo ""
    echo "Check access log:"
    tail -3 /var/log/nginx/od_emoment_tech_access.log 2>/dev/null || echo "Still no entries"
else
    echo "✗ Config invalid!"
    exit 1
fi

