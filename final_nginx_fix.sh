#!/bin/bash
# Final fix for nginx 404 - ensure proper configuration
# Run with: sudo ./final_nginx_fix.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Final Nginx Configuration Fix"
echo "=========================================="
echo ""

# 1. Copy updated config
echo "1. Copying updated configuration..."
cp "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/od_emoment_tech.conf
echo "✓ Config copied"
echo ""

# 2. Test config
echo "2. Testing configuration..."
if nginx -t; then
    echo "✓ Config valid"
else
    echo "✗ Config invalid!"
    exit 1
fi
echo ""

# 3. Create log directory if needed
echo "3. Ensuring log directory exists..."
mkdir -p /var/log/nginx
touch /var/log/nginx/od_emoment_tech_access.log
touch /var/log/nginx/od_emoment_tech_error.log
chown www-data:www-data /var/log/nginx/od_emoment_tech*.log 2>/dev/null || chown nginx:nginx /var/log/nginx/od_emoment_tech*.log 2>/dev/null || true
echo "✓ Logs ready"
echo ""

# 4. Restart nginx
echo "4. Restarting nginx..."
systemctl restart nginx
sleep 2
echo "✓ Nginx restarted"
echo ""

# 5. Test
echo "5. Testing..."
echo "Testing HTTPS with Host header:"
curl -k -I -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1 | head -5
echo ""

echo "=========================================="
echo "Check logs if still having issues:"
echo "  sudo tail -f /var/log/nginx/od_emoment_tech_error.log"
echo "  sudo tail -f /var/log/nginx/od_emoment_tech_access.log"
echo "=========================================="

