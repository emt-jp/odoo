#!/bin/bash
# Check nginx.conf structure - run with sudo
# Usage: sudo ./check_nginx_conf_structure.sh

echo "=========================================="
echo "Checking Nginx Configuration Structure"
echo "=========================================="
echo ""

NGINX_CONF="/etc/nginx/nginx.conf"

# 1. Check where include is located
echo "1. Finding include directive location:"
echo "----------------------------------------"
grep -n "include.*conf.d" "$NGINX_CONF" | head -5
echo ""

# 2. Show context around include
echo "2. Context around include directive:"
echo "----------------------------------------"
grep -B 10 -A 10 "include.*conf.d" "$NGINX_CONF" | head -25
echo ""

# 3. Check http block structure
echo "3. HTTP block structure:"
echo "----------------------------------------"
grep -n "^http\|^server\|^}" "$NGINX_CONF" | head -20
echo ""

# 4. Check if include is inside http block
echo "4. Checking if include is in http context:"
echo "----------------------------------------"
# Count http blocks before include
HTTP_BLOCKS=$(sed -n '/^http {/,/include.*conf.d/p' "$NGINX_CONF" | grep -c "^http {" || echo "0")
if [ "$HTTP_BLOCKS" -gt 0 ]; then
    echo "✓ Include appears to be in http context"
else
    echo "✗ Include might NOT be in http context!"
    echo "This would cause config files to be included in wrong context"
fi
echo ""

# 5. Show the actual structure
echo "5. Full nginx.conf structure (first 80 lines):"
echo "----------------------------------------"
head -80 "$NGINX_CONF"
echo ""

echo "=========================================="
echo "The include should be inside 'http {' block,"
echo "NOT inside a 'server {' block."
echo "=========================================="

