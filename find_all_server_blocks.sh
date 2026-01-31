#!/bin/bash
# Find all server blocks - run with sudo
# Usage: sudo ./find_all_server_blocks.sh

echo "=========================================="
echo "Finding All Server Blocks on Port 443"
echo "=========================================="
echo ""

# Get full config and extract server blocks
nginx -T 2>/dev/null | awk '
/^[[:space:]]*server[[:space:]]*{/ {
    in_server = 1
    server_num++
    print "\n=== Server Block #" server_num " ==="
}
in_server {
    if (/listen.*443/) {
        print "LISTEN: " $0
    }
    if (/server_name/) {
        print "SERVER_NAME: " $0
    }
    if (/default_server/) {
        print "DEFAULT_SERVER: YES"
    }
    if (/^[[:space:]]*}/ && in_server) {
        in_server = 0
        print "---"
    }
}' | head -50

echo ""
echo "=========================================="
echo "Checking which server block nginx would use"
echo "for Host: od.emoment.tech"
echo "=========================================="

# Test with different approaches
echo ""
echo "Testing with actual request..."
curl -v -k -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1 | grep -E "< HTTP|> Host|server:" | head -5

echo ""
echo "=========================================="

