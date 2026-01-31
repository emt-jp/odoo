#!/bin/bash
# Check if nginx proxy is actually working
# Run with: sudo ./check_nginx_proxy.sh

echo "=========================================="
echo "Nginx Proxy Debugging"
echo "=========================================="
echo ""

# 1. Make a test request and capture logs
echo "1. Making test request..."
curl -s -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health > /dev/null 2>&1
sleep 1

# 2. Check access log
echo "2. Recent access log entries:"
echo "----------------------------------------"
tail -5 /var/log/nginx/od_emoment_tech_access.log 2>/dev/null || echo "No access log entries"
echo ""

# 3. Check for actual errors (not epoll debug)
echo "3. Actual errors (filtered):"
echo "----------------------------------------"
grep -E "error|failed|connect|upstream" /var/log/nginx/od_emoment_tech_error.log 2>/dev/null | tail -10 || echo "No errors found"
echo ""

# 4. Check what upstream_port resolves to
echo "4. Testing map variable resolution:"
echo "----------------------------------------"
# Create a test to see what nginx sees
echo "Testing with different Host headers..."
for host in "od.emoment.tech" "localhost" "test"; do
    echo -n "Host: $host -> "
    # We can't directly test the variable, but we can see if proxy works
    curl -s -k -H "Host: $host" -o /dev/null -w "%{http_code}" https://127.0.0.1/web/health 2>/dev/null
    echo ""
done
echo ""

# 5. Check if Odoo is accessible
echo "5. Testing direct Odoo connection:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -3
echo ""

# 6. Check nginx config for the actual proxy_pass line
echo "6. Checking proxy_pass configuration:"
echo "----------------------------------------"
grep -A 2 "proxy_pass" /etc/nginx/conf.d/od_emoment_tech.conf | head -5
echo ""

# 7. Test if variable syntax is the issue
echo "7. Testing with explicit port (bypassing map):"
echo "----------------------------------------"
# We can't easily test this without modifying config, but let's check if the issue is the variable
echo "If this works, the issue is with the map variable"
echo ""

echo "=========================================="
echo "Key Check: Look at access logs to see:"
echo "  - What URL is being requested"
echo "  - What status code is returned"
echo "  - What upstream is being used"
echo "=========================================="

