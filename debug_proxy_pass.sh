#!/bin/bash
# Debug proxy_pass issue
# Run with: sudo ./debug_proxy_pass.sh

echo "=========================================="
echo "Debugging proxy_pass Configuration"
echo "=========================================="
echo ""

# 1. Check what nginx sees for the Host header
echo "1. Testing with explicit Host header:"
echo "----------------------------------------"
curl -v -H "Host: od.emoment.tech" http://127.0.0.1/ 2>&1 | grep -E "> Host|> GET|< HTTP" | head -5
echo ""

# 2. Check if proxy_pass URL is being constructed correctly
echo "2. Checking proxy_pass configuration:"
echo "----------------------------------------"
grep -A 10 "location /" /etc/nginx/conf.d/od_emoment_tech.conf | head -12
echo ""

# 3. Test if the variable is being set
echo "3. Testing map variable resolution:"
echo "----------------------------------------"
# Create a test config to see what nginx resolves
echo "Testing if map works..."
nginx -T 2>/dev/null | grep -A 20 "map \$host \$upstream_port" | head -25
echo ""

# 4. Check nginx error logs for proxy errors
echo "4. Checking for proxy-related errors:"
echo "----------------------------------------"
tail -30 /var/log/nginx/error.log 2>/dev/null | grep -i "proxy\|upstream\|connect" | tail -10 || echo "No proxy errors found"
echo ""

# 5. Test direct connection to Odoo
echo "5. Testing direct Odoo connection:"
echo "----------------------------------------"
curl -I http://127.0.0.1:8069/web/health 2>&1 | head -5
echo ""

# 6. Check if there are multiple server blocks on 443
echo "6. All server blocks on port 443:"
echo "----------------------------------------"
grep -r "listen.*443" /etc/nginx/ 2>/dev/null | grep -v "^#" | grep -v "backup"
echo ""

# 7. Check server_name matching
echo "7. Server name configuration:"
echo "----------------------------------------"
grep -A 2 "server_name" /etc/nginx/conf.d/od_emoment_tech.conf | head -5
echo ""

# 8. Test with actual domain (if DNS resolves locally)
echo "8. Testing with actual domain resolution:"
echo "----------------------------------------"
# Add 127.0.0.1 od.emoment.tech to /etc/hosts temporarily for testing
if grep -q "od.emoment.tech" /etc/hosts 2>/dev/null; then
    curl -I http://od.emoment.tech/ 2>&1 | head -5
else
    echo "od.emoment.tech not in /etc/hosts, skipping direct test"
fi
echo ""

echo "=========================================="
echo "Key Insight:"
echo "When testing HTTP (port 80), the default_server might catch it."
echo "When testing HTTPS (port 443), check if SSL is working and"
echo "if the server_name matches correctly."
echo "=========================================="

