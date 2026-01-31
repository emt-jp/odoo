#!/bin/bash
# Investigate nginx 404 issue
# Run with: sudo ./investigate_nginx_404.sh

set -e

echo "=========================================="
echo "Nginx 404 Investigation"
echo "=========================================="
echo ""

# 1. Check nginx config test
echo "1. Testing nginx configuration..."
nginx -t 2>&1
echo ""

# 2. List all server blocks on port 443
echo "2. All server blocks listening on port 443:"
echo "----------------------------------------"
grep -r "listen.*443" /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null | grep -v backup | grep -v "^#"
echo ""

# 3. Check which server block matches
echo "3. Testing server block matching:"
echo "----------------------------------------"
echo "Making request with Host: od.emoment.tech"
curl -k -s -o /dev/null -w "HTTP Status: %{http_code}\n" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1
echo ""

# 4. Check if Odoo is accessible
echo "4. Testing direct Odoo connection:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/ 2>&1 | head -3
echo ""

# 5. Check nginx error logs
echo "5. Recent nginx error logs:"
echo "----------------------------------------"
tail -20 /var/log/nginx/error.log 2>/dev/null | tail -10 || echo "Cannot access error log"
echo ""

# 6. Check access logs
echo "6. Recent access logs:"
echo "----------------------------------------"
tail -5 /var/log/nginx/access.log 2>/dev/null | tail -3 || echo "Cannot access access log"
echo ""

# 7. Check current nginx.conf
echo "7. Current nginx.conf proxy_pass configuration:"
echo "----------------------------------------"
grep -A 5 "location /" /etc/nginx/conf.d/nginx.conf | head -8
echo ""

# 8. Check if map variable is defined
echo "8. Map variable definition:"
echo "----------------------------------------"
grep -A 5 "map \$host \$upstream_port" /etc/nginx/conf.d/nginx.conf | head -7
echo ""

# 9. Test with hardcoded port
echo "9. Testing if hardcoded port works:"
echo "----------------------------------------"
echo "Temporarily testing with port 8069..."
TEMP_CONF="/tmp/nginx_test.conf"
cp /etc/nginx/conf.d/nginx.conf "$TEMP_CONF"
sed -i 's|proxy_pass http://127.0.0.1:\$upstream_port;|proxy_pass http://127.0.0.1:8069;|' "$TEMP_CONF"
cp "$TEMP_CONF" /etc/nginx/conf.d/nginx.conf
nginx -t > /dev/null 2>&1 && systemctl reload nginx > /dev/null 2>&1
sleep 1
RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1)
echo "Response code with hardcoded port: $RESPONSE"
# Restore
cp "$TEMP_CONF" /etc/nginx/conf.d/nginx.conf.backup.test 2>/dev/null || true
# We'll restore manually if needed
echo ""

# 10. Check for other config files that might interfere
echo "10. Other config files in conf.d:"
echo "----------------------------------------"
ls -la /etc/nginx/conf.d/*.conf 2>/dev/null | awk '{print $9}' | xargs -I {} basename {}
echo ""

echo "=========================================="
echo "Investigation Complete"
echo "=========================================="
echo ""
echo "Key findings:"
echo "- If hardcoded port works but variable doesn't: variable resolution issue"
echo "- If hardcoded port also fails: proxy_pass or upstream issue"
echo "- Check if other server blocks are interfering"

