#!/bin/bash
# Force apply config and verify - run with sudo
# Usage: sudo ./force_apply_config.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SOURCE="${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf"
CONFIG_TARGET="/etc/nginx/conf.d/od_emoment_tech.conf"

echo "=========================================="
echo "Force Apply Nginx Configuration"
echo "=========================================="
echo ""

# 1. Backup
echo "1. Backing up current config..."
if [ -f "$CONFIG_TARGET" ]; then
    cp "$CONFIG_TARGET" "${CONFIG_TARGET}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✓ Backup created"
else
    echo "No existing config to backup"
fi
echo ""

# 2. Copy config
echo "2. Copying new configuration..."
cp "$CONFIG_SOURCE" "$CONFIG_TARGET"
chmod 644 "$CONFIG_TARGET"
chown root:root "$CONFIG_TARGET"
echo "✓ Config copied"
echo ""

# 3. Verify upstream blocks exist
echo "3. Verifying upstream blocks in config..."
if grep -q "upstream odoo_backend" "$CONFIG_TARGET"; then
    echo "✓ upstream odoo_backend found"
else
    echo "✗ upstream odoo_backend NOT FOUND!"
    exit 1
fi

if grep -q "proxy_pass http://odoo_backend" "$CONFIG_TARGET"; then
    echo "✓ proxy_pass http://odoo_backend found"
else
    echo "✗ proxy_pass http://odoo_backend NOT FOUND!"
    exit 1
fi
echo ""

# 4. Test config
echo "4. Testing nginx configuration..."
if nginx -t 2>&1; then
    echo "✓ Config test passed"
else
    echo "✗ Config test FAILED!"
    exit 1
fi
echo ""

# 5. Verify upstream is loaded
echo "5. Verifying upstream is loaded in nginx..."
if nginx -T 2>/dev/null | grep -q "upstream odoo_backend"; then
    echo "✓ Upstream is loaded"
else
    echo "⚠ Upstream not found - need to reload nginx"
fi
echo ""

# 6. Restart nginx (not just reload)
echo "6. Restarting nginx..."
systemctl restart nginx
sleep 2
echo "✓ Nginx restarted"
echo ""

# 7. Verify again
echo "7. Verifying upstream is now loaded..."
if nginx -T 2>/dev/null | grep -q "upstream odoo_backend"; then
    echo "✓ Upstream is now loaded"
else
    echo "✗ Upstream still not found after restart!"
    echo "Showing nginx -T output:"
    nginx -T 2>&1 | grep -A 5 "upstream" | head -10
    exit 1
fi
echo ""

# 8. Test
echo "8. Testing connection..."
sleep 1
curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
echo ""

echo "=========================================="
echo "✅ Configuration Applied!"
echo "=========================================="
echo ""
echo "Test your site:"
echo "  curl -I https://od.emoment.tech"
echo ""

