#!/bin/bash
# Deep debugging - run with sudo
# Usage: sudo ./deep_debug.sh

echo "=========================================="
echo "Deep Debugging"
echo "=========================================="
echo ""

# 1. Check all server blocks
echo "1. All server blocks in nginx:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -B 3 "listen.*443" | grep -E "server_name|listen" | head -15
echo ""

# 2. Check the exact location block
echo "2. Location / block configuration:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -A 15 "location / {" | grep -A 15 "proxy_pass" | head -20
echo ""

# 3. Test direct connection to upstream
echo "3. Testing direct connection to upstream:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -5
echo ""

# 4. Test with verbose curl to see what's happening
echo "4. Verbose test request:"
echo "----------------------------------------"
curl -v -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | grep -E "< HTTP|> Host|upstream|proxy" | head -10
echo ""

# 5. Check if there are any other config files
echo "5. Other config files that might interfere:"
echo "----------------------------------------"
ls -la /etc/nginx/conf.d/*.conf 2>/dev/null | grep -v od_emoment
echo ""

# 6. Check main access log
echo "6. Main access log (last 3 entries):"
echo "----------------------------------------"
tail -3 /var/log/nginx/access.log 2>/dev/null || echo "No main access log"
echo ""

# 7. Check if server block is actually matching
echo "7. Testing server block matching:"
echo "----------------------------------------"
# Add a test response header to see if our block matches
echo "If our block matches, we should see proxy headers"
curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -10
echo ""

echo "=========================================="
echo "Key Question: Why is access log empty?"
echo "This suggests the server block or location"
echo "block isn't executing at all."
echo "=========================================="

