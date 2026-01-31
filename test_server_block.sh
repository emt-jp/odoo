#!/bin/bash
# Test if server block is matching - run with sudo
# Usage: sudo ./test_server_block.sh

echo "=========================================="
echo "Testing Server Block Matching"
echo "=========================================="
echo ""

# Temporarily modify config to return a test response
CONFIG="/etc/nginx/conf.d/od_emoment_tech.conf"
BACKUP="${CONFIG}.test_backup"

# Backup
cp "$CONFIG" "$BACKUP"

# Add a test location that returns a specific response
echo "Adding test location block..."
sed -i '/location \/ {/a\        return 200 "SERVER_BLOCK_MATCHING";\n        add_header Content-Type text/plain;\n        #' "$CONFIG"

# Test config
if nginx -t 2>&1; then
    echo "✓ Config valid, reloading..."
    systemctl reload nginx
    sleep 1
    
    echo "Testing..."
    RESPONSE=$(curl -s -k -H "Host: od.emoment.tech" https://127.0.0.1/)
    if echo "$RESPONSE" | grep -q "SERVER_BLOCK_MATCHING"; then
        echo "✓ SERVER BLOCK IS MATCHING!"
        echo "Response: $RESPONSE"
    else
        echo "✗ Server block NOT matching"
        echo "Response: $RESPONSE"
    fi
else
    echo "✗ Config invalid"
fi

# Restore
mv "$BACKUP" "$CONFIG"
systemctl reload nginx

echo ""
echo "=========================================="

