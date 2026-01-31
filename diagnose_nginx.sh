#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo ./diagnose_nginx.sh"
    exit 1
fi

echo "========================================="
echo "Nginx Diagnostic Report"
echo "========================================="
echo ""

echo "[1] All nginx processes:"
ps aux | grep nginx | grep -v grep
echo ""

echo "[2] Nginx listening on port 443:"
netstat -tlnp | grep :443
echo ""

echo "[3] All nginx config files in /etc/nginx/conf.d/:"
ls -lh /etc/nginx/conf.d/*.conf 2>/dev/null
echo ""

echo "[4] Server blocks with 'emoment' in /etc/nginx/:"
grep -r "server_name.*emoment" /etc/nginx/ 2>/dev/null | grep -v backup | grep -v "#"
echo ""

echo "[5] Current active configuration for odoo/od:"
echo "--- /etc/nginx/conf.d/nginx.conf ---"
grep -A 5 "server_name" /etc/nginx/conf.d/nginx.conf | head -20
echo ""

echo "[6] Testing Host headers:"
echo "  Testing: od.emoment.tech"
curl -k -s -o /dev/null -w "    HTTP %{http_code}\n" -H "Host: od.emoment.tech" https://127.0.0.1/web

echo "  Testing: odoo.emoment.tech"
curl -k -s -o /dev/null -w "    HTTP %{http_code}\n" -H "Host: odoo.emoment.tech" https://127.0.0.1/web

echo ""
echo "[7] Checking for other web servers/proxies:"
netstat -tlnp | grep -E ":(80|443|8080|8443)" | grep -v nginx
echo ""

echo "[8] Recent nginx error log:"
tail -10 /var/log/nginx/error.log 2>/dev/null || echo "Cannot read error log"
echo ""

echo "========================================="
echo "End of Diagnostic Report"
echo "========================================="
