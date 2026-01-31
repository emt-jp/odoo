#!/bin/bash
# Debug nginx 404 errors
# Run with: sudo ./debug_nginx_404.sh

set -e

echo "=========================================="
echo "Debugging Nginx 404 Error"
echo "=========================================="
echo ""

# Check nginx config
echo "1. Checking nginx configuration..."
nginx -t 2>&1
echo ""

# Check if config file is loaded
echo "2. Checking loaded configuration files..."
ls -la /etc/nginx/conf.d/*.conf 2>/dev/null || echo "No config files in conf.d"
echo ""

# Check error logs
echo "3. Recent error logs (last 20 lines):"
tail -20 /var/log/nginx/error.log 2>/dev/null || journalctl -u nginx --no-pager -n 20 | tail -20
echo ""

# Check access logs
echo "4. Recent access logs (last 10 lines):"
tail -10 /var/log/nginx/access.log 2>/dev/null || echo "No access.log found"
echo ""

# Test Odoo directly
echo "5. Testing Odoo directly on port 8069:"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -10
echo ""

# Test nginx proxy with correct host header
echo "6. Testing nginx proxy with Host header:"
curl -I -H "Host: od.emoment.tech" http://127.0.0.1/ 2>&1 | head -10
echo ""

# Check if upstream_port variable is being set
echo "7. Checking nginx configuration for map variables:"
grep -A 15 "map \$host" /etc/nginx/conf.d/od_emoment_tech.conf 2>/dev/null || echo "Config file not found"
echo ""

# Check what port nginx thinks it should use
echo "8. Testing with verbose curl to see what's happening:"
curl -v -H "Host: od.emoment.tech" http://127.0.0.1/ 2>&1 | grep -E "< HTTP|upstream|proxy" | head -10
echo ""

# Check if default server is interfering
echo "9. Checking for default server blocks:"
grep -r "default_server" /etc/nginx/ 2>/dev/null | head -5 || echo "No default_server found"
echo ""

echo "=========================================="
echo "Diagnostics Complete"
echo "=========================================="

