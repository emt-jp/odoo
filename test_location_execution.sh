#!/bin/bash
# Test if location block executes - run with sudo
# Usage: sudo ./test_location_execution.sh

set -e

CONFIG="/etc/nginx/conf.d/od_emoment_tech.conf"
BACKUP="${CONFIG}.exec_test_backup"

echo "=========================================="
echo "Testing Location Block Execution"
echo "=========================================="
echo ""

# Backup
cp "$CONFIG" "$BACKUP"

# Replace proxy_pass with a simple return that will definitely show
echo "Modifying location block to return test message..."
sed -i '/location \/ {/,/^    }/c\
    location / {\
        return 200 "LOCATION_BLOCK_EXECUTING\n";\
        add_header Content-Type text/plain;\
    }' "$CONFIG"

# But wait, that's too aggressive - it will replace the whole block
# Let me do it more carefully
mv "$BACKUP" "$CONFIG"

# More careful - just replace proxy_pass line
sed -i 's|proxy_pass http://odoo_backend;|return 200 "LOCATION_BLOCK_EXECUTING\\n"; add_header Content-Type text/plain;|' "$CONFIG"

# Test
if nginx -t 2>&1; then
    echo "✓ Config valid, reloading..."
    systemctl reload nginx
    sleep 1
    
    echo "Testing..."
    RESPONSE=$(curl -s -k -H "Host: od.emoment.tech" https://127.0.0.1/)
    if echo "$RESPONSE" | grep -q "LOCATION_BLOCK_EXECUTING"; then
        echo "✓✓✓ LOCATION BLOCK IS EXECUTING!"
        echo "Response: $RESPONSE"
        echo ""
        echo "This means the location block works, but proxy_pass is failing."
    else
        echo "✗ Location block NOT executing"
        echo "Got: $RESPONSE"
        echo ""
        echo "This means the location block isn't matching or executing at all."
    fi
else
    echo "✗ Config invalid!"
fi

# Restore
mv "$BACKUP" "$CONFIG"
systemctl reload nginx

echo ""
echo "=========================================="

