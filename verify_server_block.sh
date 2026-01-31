#!/bin/bash
# Verify which server block is handling requests
# Run with: sudo ./verify_server_block.sh

echo "=========================================="
echo "Verifying Server Block Matching"
echo "=========================================="
echo ""

# 1. Check all server blocks on 443
echo "1. All server blocks listening on 443:"
echo "----------------------------------------"
grep -r "listen.*443" /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "^#" | grep -v "backup" | while read line; do
    file=$(echo "$line" | cut -d: -f1)
    config=$(echo "$line" | cut -d: -f2-)
    echo "File: $file"
    echo "  $config"
    # Get server_name
    grep -A 5 "listen.*443" "$file" 2>/dev/null | grep "server_name" | head -1
    echo ""
done
echo ""

# 2. Test with explicit Host header
echo "2. Testing with Host: od.emoment.tech"
echo "----------------------------------------"
curl -v -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | grep -E "< HTTP|> Host|server:" | head -5
echo ""

# 3. Check if our config file is actually loaded
echo "3. Checking if config is loaded:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -A 10 "server_name.*od.emoment.tech" | head -15
echo ""

# 4. Test if default_server is working
echo "4. Testing without Host header (should use default_server):"
echo "----------------------------------------"
curl -v -k https://127.0.0.1/web/health 2>&1 | grep -E "< HTTP|> Host" | head -3
echo ""

# 5. Check main error log for any clues
echo "5. Recent main error log entries:"
echo "----------------------------------------"
tail -10 /var/log/nginx/error.log 2>/dev/null | grep -v "epoll" | tail -5 || echo "No errors"
echo ""

echo "=========================================="
echo "Key Insight:"
echo "If our server block isn't matching, check:"
echo "  1. Is the config file actually loaded?"
echo "  2. Is there another server block with higher priority?"
echo "  3. Is the server_name matching correctly?"
echo "=========================================="

