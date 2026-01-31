#!/bin/bash
# Quick check of nginx status and config
# Run with: sudo ./check_nginx_status.sh

echo "=========================================="
echo "Nginx Status Check"
echo "=========================================="
echo ""

# 1. Check if config file has defaults
echo "1. Checking config file for default values:"
echo "----------------------------------------"
if grep -q "default 8069" /etc/nginx/conf.d/od_emoment_tech.conf 2>/dev/null; then
    echo "✓ Config has default 8069"
else
    echo "✗ Config MISSING default 8069 - needs update!"
fi

if grep -q "default 8072" /etc/nginx/conf.d/od_emoment_tech.conf 2>/dev/null; then
    echo "✓ Config has default 8072"
else
    echo "✗ Config MISSING default 8072 - needs update!"
fi
echo ""

# 2. Check nginx config test
echo "2. Testing nginx configuration:"
echo "----------------------------------------"
nginx -t 2>&1
echo ""

# 3. Check recent errors
echo "3. Recent error log entries (last 10):"
echo "----------------------------------------"
tail -10 /var/log/nginx/error.log 2>/dev/null | tail -10 || journalctl -u nginx --no-pager -n 10 | grep -i error | tail -10
echo ""

# 4. Check recent access logs for od.emoment.tech
echo "4. Recent access logs for od.emoment.tech (last 5):"
echo "----------------------------------------"
grep "od.emoment.tech" /var/log/nginx/access.log 2>/dev/null | tail -5 || echo "No access.log found or no entries"
echo ""

# 5. Test local proxy
echo "5. Testing local proxy with Host header:"
echo "----------------------------------------"
curl -v -H "Host: od.emoment.tech" http://127.0.0.1/ 2>&1 | grep -E "< HTTP|upstream|proxy" | head -5
echo ""

# 6. Check what server block matches
echo "6. Checking server blocks:"
echo "----------------------------------------"
grep -r "listen.*443" /etc/nginx/conf.d/ 2>/dev/null | grep -v "^#" | head -5
echo ""

# 7. Check if default server exists
echo "7. Checking for default server blocks:"
echo "----------------------------------------"
grep -r "default_server" /etc/nginx/ 2>/dev/null | head -3
echo ""

echo "=========================================="
echo "If config is missing defaults, run:"
echo "  sudo cp ~/ws/odoo/ops/nginx/conf.d/od_emoment_tech.conf /etc/nginx/conf.d/"
echo "  sudo nginx -t"
echo "  sudo systemctl restart nginx"
echo "=========================================="

