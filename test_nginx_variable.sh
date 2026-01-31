#!/bin/bash
# Test if nginx variable resolution is the issue
# This will temporarily modify the config to test

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

CONF="/etc/nginx/conf.d/nginx.conf"
BACKUP="/etc/nginx/conf.d/nginx.conf.test_backup"

echo "=========================================="
echo "Testing Nginx Variable Resolution"
echo "=========================================="
echo ""

# Backup
cp "$CONF" "$BACKUP"
echo "✓ Backed up config to $BACKUP"

# Test 1: Check current config
echo ""
echo "1. Current proxy_pass line:"
grep "proxy_pass.*upstream_port" "$CONF"

# Test 2: Try with hardcoded port
echo ""
echo "2. Testing with hardcoded port 8069..."
sed -i 's|proxy_pass http://127.0.0.1:\$upstream_port;|proxy_pass http://127.0.0.1:8069;|' "$CONF"

if nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Config test passed"
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    
    echo ""
    echo "3. Testing connection..."
    sleep 1
    RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>/dev/null)
    
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "303" ] || [ "$RESPONSE" = "302" ]; then
        echo "✓ SUCCESS! Got HTTP $RESPONSE"
        echo ""
        echo "This confirms the issue is with variable resolution in proxy_pass."
        echo "The variable \$upstream_port is not being resolved correctly."
    else
        echo "✗ Still getting HTTP $RESPONSE"
        echo "The issue might be something else."
    fi
else
    echo "✗ Config test failed"
fi

# Restore backup
echo ""
echo "4. Restoring original config..."
cp "$BACKUP" "$CONF"
nginx -t > /dev/null 2>&1 && systemctl reload nginx
echo "✓ Config restored"

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="

