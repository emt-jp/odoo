#!/bin/bash
# Check location block - run with sudo
# Usage: sudo ./check_location_block.sh

echo "=========================================="
echo "Checking Location Block Configuration"
echo "=========================================="
echo ""

# 1. Show full server block
echo "1. Full server block for od.emoment.tech:"
echo "----------------------------------------"
nginx -T 2>/dev/null | awk '/server_name.*od.emoment.tech/,/^[[:space:]]*server[[:space:]]*{|^[[:space:]]*}/' | head -50
echo ""

# 2. Show location block specifically
echo "2. Location / block:"
echo "----------------------------------------"
nginx -T 2>/dev/null | awk '/server_name.*od.emoment.tech/,/^[[:space:]]*}/' | grep -A 15 "location /" | head -20
echo ""

# 3. Check upstream
echo "3. Upstream odoo_backend:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -A 3 "upstream odoo_backend"
echo ""

# 4. Make test request and check logs
echo "4. Making test request..."
curl -s -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health > /dev/null
sleep 1
echo ""

# 5. Check access log
echo "5. Access log after request:"
echo "----------------------------------------"
tail -3 /var/log/nginx/od_emoment_tech_access.log 2>/dev/null || echo "No entries"
echo ""

# 6. Check error log
echo "6. Recent error log entries:"
echo "----------------------------------------"
tail -10 /var/log/nginx/error.log 2>/dev/null | grep -v "epoll" | tail -5 || echo "No errors"
echo ""

# 7. Check main access log
echo "7. Main access log (last 3 entries):"
echo "----------------------------------------"
tail -3 /var/log/nginx/access.log 2>/dev/null || echo "No entries"
echo ""

echo "=========================================="
echo "If location block is missing or proxy_pass"
echo "is wrong, that explains the 404."
echo "=========================================="

