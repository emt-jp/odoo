#!/bin/bash
# Final diagnosis - run with sudo
# Usage: sudo ./final_diagnosis.sh

echo "=========================================="
echo "Final Diagnosis"
echo "=========================================="
echo ""

# 1. Check if upstream is defined
echo "1. Checking if upstream blocks are loaded:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -A 3 "upstream odoo_backend" | head -5
echo ""

# 2. Check proxy_pass in active config
echo "2. Active proxy_pass configuration:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -B 2 -A 5 "location /" | grep -A 5 "proxy_pass" | head -8
echo ""

# 3. Check server blocks
echo "3. Server blocks on 443:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -B 5 "listen.*443" | grep -E "server_name|listen" | head -10
echo ""

# 4. Make test request
echo "4. Making test request:"
echo "----------------------------------------"
curl -v -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | grep -E "< HTTP|> Host|upstream" | head -5
echo ""

# 5. Check logs after request
echo "5. Access log after request:"
echo "----------------------------------------"
sleep 1
tail -3 /var/log/nginx/od_emoment_tech_access.log 2>/dev/null || echo "No entries"
echo ""

# 6. Check for errors
echo "6. Recent errors:"
echo "----------------------------------------"
tail -10 /var/log/nginx/error.log 2>/dev/null | grep -E "error|warn|failed" | tail -5 || echo "No errors"
echo ""

echo "=========================================="
echo "If upstream is not found, the config"
echo "wasn't loaded. Check nginx -t for errors."
echo "=========================================="

