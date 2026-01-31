#!/bin/bash
# Simple test - modify location to return text instead of proxy
# Run with: sudo ./simple_location_test.sh

set -e

CONFIG="/etc/nginx/conf.d/od_emoment_tech.conf"
BACKUP="${CONFIG}.simple_test_backup"

echo "=========================================="
echo "Simple Location Block Test"
echo "=========================================="
echo ""

# Backup
cp "$CONFIG" "$BACKUP"

# Replace proxy_pass with simple return
echo "Modifying location block to return text..."
sed -i '/location \/ {/,/^    }/c\
    location / {\
        return 200 "LOCATION_BLOCK_WORKING\n";\
        add_header Content-Type text/plain;\
    }' "$CONFIG"

# But wait, that's too aggressive. Let me do it more carefully
# Restore first
mv "$BACKUP" "$CONFIG"

# More careful replacement - just the proxy_pass line
sed -i 's|proxy_pass http://odoo_backend;|return 200 "LOCATION_BLOCK_WORKING\\n"; add_header Content-Type text/plain;|' "$CONFIG"

# Test
if nginx -t 2>&1; then
    echo "✓ Config valid, reloading..."
    systemctl reload nginx
    sleep 1
    
    echo "Testing..."
    RESPONSE=$(curl -s -k -H "Host: od.emoment.tech" https://127.0.0.1/)
    if echo "$RESPONSE" | grep -q "LOCATION_BLOCK_WORKING"; then
        echo "✓✓✓ LOCATION BLOCK IS WORKING!"
        echo "Response: $RESPONSE"
    else
        echo "✗ Location block NOT working"
        echo "Got: $RESPONSE"
    fi
else
    echo "✗ Config invalid"
fi

# Restore
mv "$BACKUP" "$CONFIG"
systemctl reload nginx

echo ""
echo "=========================================="

