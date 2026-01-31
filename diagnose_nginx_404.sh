#!/bin/bash
# Diagnose nginx 404 error - run with sudo
# Usage: sudo ./diagnose_nginx_404.sh

echo "=========================================="
echo "Nginx 404 Error Diagnosis"
echo "=========================================="
echo ""

# 1. Check nginx error logs
echo "1. ERROR LOGS (last 30 lines):"
echo "----------------------------------------"
tail -30 /var/log/nginx/error.log 2>/dev/null || journalctl -u nginx --no-pager -n 30 | grep -i error
echo ""

# 2. Check access logs  
echo "2. ACCESS LOGS (last 20 lines):"
echo "----------------------------------------"
tail -20 /var/log/nginx/access.log 2>/dev/null || echo "No access.log found"
echo ""

# 3. Check which server block is matching
echo "3. Testing server block matching:"
echo "----------------------------------------"
echo "Testing with Host: od.emoment.tech"
curl -v -H "Host: od.emoment.tech" http://127.0.0.1/ 2>&1 | grep -E "< HTTP|< Server|upstream" | head -5
echo ""

# 4. Check if map variable is working
echo "4. Checking map configuration:"
echo "----------------------------------------"
grep -A 20 "map \$host" /etc/nginx/conf.d/od_emoment_tech.conf 2>/dev/null | head -25
echo ""

# 5. Check for default server blocks
echo "5. Checking for default server blocks:"
echo "----------------------------------------"
grep -r "listen.*default_server" /etc/nginx/ 2>/dev/null | head -5
echo ""

# 6. Check all server blocks
echo "6. All server blocks listening on port 80:"
echo "----------------------------------------"
grep -r "listen 80" /etc/nginx/ 2>/dev/null | grep -v "^#" | head -10
echo ""

# 7. Test Odoo directly
echo "7. Testing Odoo directly:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -5
echo ""

# 8. Check nginx config test
echo "8. Nginx configuration test:"
echo "----------------------------------------"
nginx -t 2>&1
echo ""

echo "=========================================="
echo "If upstream_port is empty, the map isn't matching."
echo "Check that the Host header matches exactly."
echo "=========================================="

