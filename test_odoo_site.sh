#!/bin/bash

echo "========================================="
echo "Testing odoo.emoment.tech Configuration"
echo "========================================="
echo ""

# Server IP
echo "[1] Server Information:"
echo "  Public IPv4: 46.250.252.111"
echo "  Public IPv6: 2400:d320:2282:9400::1"
echo ""

# DNS Resolution
echo "[2] DNS Resolution:"
dig odoo.emoment.tech +short | head -5
echo ""

# Local backend test
echo "[3] Local Backend Test (http://127.0.0.1:8069/web):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8069/web 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
    echo "  ✓ Odoo backend responding (HTTP $HTTP_CODE)"
else
    echo "  ✗ Odoo backend issue (HTTP $HTTP_CODE)"
fi
echo ""

# Public HTTPS test
echo "[4] Public HTTPS Test (https://odoo.emoment.tech/web):"
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://odoo.emoment.tech/web 2>/dev/null)
if [ "$HTTPS_CODE" = "200" ] || [ "$HTTPS_CODE" = "303" ]; then
    echo "  ✓ Site is accessible! (HTTP $HTTPS_CODE)"
    echo ""
    echo "  Full response:"
    curl -I https://odoo.emoment.tech/web 2>/dev/null | head -10
elif [ "$HTTPS_CODE" = "404" ]; then
    echo "  ✗ Getting 404 error"
    echo ""
    echo "  This means Cloudflare cannot reach your origin server."
    echo "  Please verify in Cloudflare:"
    echo "    1. DNS A record for 'odoo' points to: 46.250.252.111"
    echo "    2. SSL/TLS mode is set to: Full (strict)"
    echo "    3. Proxy status is: Proxied (orange cloud)"
    echo ""
    echo "  See CLOUDFLARE_FIX_404.md for detailed instructions"
else
    echo "  ⚠ Unexpected response (HTTP $HTTPS_CODE)"
fi

echo ""
echo "========================================="

# Nginx status
echo ""
echo "[5] Nginx Status:"
if pgrep nginx > /dev/null; then
    echo "  ✓ Nginx is running"
    NGINX_WORKERS=$(pgrep -c "nginx: worker")
    echo "  ✓ Worker processes: $NGINX_WORKERS"
else
    echo "  ✗ Nginx is not running!"
fi

echo ""
echo "========================================="
echo "Test Complete"
echo "========================================="
