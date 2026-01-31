#!/bin/bash
# Fix server block matching - run with sudo
# Usage: sudo ./fix_server_block_match.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Fixing Server Block Matching"
echo "=========================================="
echo ""

# 1. Check for backup/duplicate config files
echo "1. Checking for duplicate/backup config files:"
echo "----------------------------------------"
find /etc/nginx/conf.d/ -name "*.conf*" -type f | grep -v od_emoment_tech.conf | while read file; do
    if grep -q "server_name.*od.emoment" "$file" 2>/dev/null; then
        echo "⚠ Found config with od.emoment.tech: $file"
        echo "   Consider removing or fixing this file"
    fi
done
echo ""

# 2. Copy updated config
echo "2. Copying updated configuration..."
cp "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/od_emoment_tech.conf
echo "✓ Config copied"
echo ""

# 3. Verify server_name includes od.emoment.tech
echo "3. Verifying server_name:"
if grep -q "server_name.*od.emoment.tech" /etc/nginx/conf.d/od_emoment_tech.conf; then
    echo "✓ server_name includes od.emoment.tech"
    grep "server_name" /etc/nginx/conf.d/od_emoment_tech.conf | head -1
else
    echo "✗ server_name doesn't include od.emoment.tech!"
    exit 1
fi
echo ""

# 4. Test config
echo "4. Testing configuration..."
if nginx -t 2>&1; then
    echo "✓ Config valid"
else
    echo "✗ Config invalid!"
    exit 1
fi
echo ""

# 5. Reload
echo "5. Reloading nginx..."
systemctl reload nginx
sleep 1
echo "✓ Nginx reloaded"
echo ""

# 6. Test
echo "6. Testing connection..."
curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
echo ""

echo "=========================================="
echo "If still 404, check for other config files:"
echo "  sudo find /etc/nginx/conf.d/ -name '*.conf*'"
echo "  sudo grep -r 'server_name.*od.emoment' /etc/nginx/conf.d/"
echo "=========================================="

