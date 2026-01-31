#!/bin/bash
# Test upstream connection - run with sudo
# Usage: sudo ./test_upstream_connection.sh

echo "=========================================="
echo "Testing Upstream Connection"
echo "=========================================="
echo ""

# 1. Check if upstream is defined
echo "1. Checking upstream definition:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -A 3 "upstream odoo_backend" | head -5
echo ""

# 2. Test direct connection
echo "2. Testing direct connection to 127.0.0.1:8069:"
echo "----------------------------------------"
curl -v http://127.0.0.1:8069/web/health 2>&1 | grep -E "< HTTP|Connection" | head -5
echo ""

# 3. Check if nginx can resolve the upstream
echo "3. Testing through nginx with a simple test:"
echo "----------------------------------------"
# Create a test config that just returns the upstream status
echo "Checking if nginx can reach upstream..."

# Test with curl through nginx
curl -v -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | grep -E "< HTTP|upstream|Connection|error" | head -10
echo ""

# 4. Check error log for upstream errors
echo "4. Checking for upstream connection errors:"
echo "----------------------------------------"
tail -50 /var/log/nginx/error.log 2>/dev/null | grep -i "upstream\|connect\|failed" | tail -10 || echo "No upstream errors found"
echo ""

# 5. Test if maybe the issue is with the Host header
echo "5. Testing with different Host headers:"
echo "----------------------------------------"
for host in "od.emoment.tech" "localhost" "127.0.0.1"; do
    echo -n "Host: $host -> "
    curl -s -k -H "Host: $host" -o /dev/null -w "%{http_code}" https://127.0.0.1/web/health 2>/dev/null
    echo ""
done
echo ""

echo "=========================================="
echo "If all return 404, the server block isn't"
echo "matching. If some work, it's a Host header issue."
echo "=========================================="

