#!/bin/bash

echo "Checking active nginx configuration..."
echo "======================================="
echo ""

echo "Current server_name in /etc/nginx/conf.d/nginx.conf:"
sudo grep -E "server_name|listen" /etc/nginx/conf.d/nginx.conf | head -20

echo ""
echo "======================================="
echo "Testing Host Headers:"
echo "======================================="
echo ""

echo "[1] Testing with Host: od.emoment.tech"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://46.250.252.111/web 2>/dev/null)
echo "    Result: HTTP $HTTP_CODE"

echo ""
echo "[2] Testing with Host: odoo.emoment.tech"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: odoo.emoment.tech" https://46.250.252.111/web 2>/dev/null)
echo "    Result: HTTP $HTTP_CODE"

echo ""
echo "======================================="
