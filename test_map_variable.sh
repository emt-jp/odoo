#!/bin/bash
# Test if map variable is working
# Run with: sudo ./test_map_variable.sh

echo "=========================================="
echo "Testing Map Variable Resolution"
echo "=========================================="
echo ""

# The issue might be that proxy_pass with variable needs special handling
# Let's create a test config to see what's happening

echo "1. Checking current proxy_pass configuration:"
echo "----------------------------------------"
grep -A 2 "proxy_pass" /etc/nginx/conf.d/od_emoment_tech.conf | head -5
echo ""

echo "2. Testing if Odoo responds on port 8069:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -3
echo ""

echo "3. The issue might be that when proxy_pass uses a variable,"
echo "   nginx needs the variable to be resolved correctly."
echo ""
echo "   If \$upstream_port is empty, proxy_pass becomes:"
echo "   proxy_pass http://127.0.0.1:;"
echo "   Which is invalid and causes 404"
echo ""

echo "4. Let's verify the map has a default:"
echo "----------------------------------------"
grep -A 15 "map \$host \$upstream_port" /etc/nginx/conf.d/od_emoment_tech.conf | head -18
echo ""

echo "=========================================="
echo "Solution: Let's try using an upstream block"
echo "instead of a variable in proxy_pass"
echo "=========================================="

