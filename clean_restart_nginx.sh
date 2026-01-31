#!/bin/bash
# Clean restart nginx - remove backups and restart
# Run with: sudo ./clean_restart_nginx.sh

set -e

echo "=========================================="
echo "Clean Restart Nginx"
echo "=========================================="
echo ""

# 1. Remove backup files
echo "1. Removing backup files..."
find /etc/nginx/conf.d/ -name "*.backup*" -type f -delete
echo "✓ Backup files removed"
echo ""

# 2. Verify only one config file exists
echo "2. Config files remaining:"
ls -la /etc/nginx/conf.d/*.conf 2>/dev/null | grep -v backup || echo "No .conf files found"
echo ""

# 3. Test config
echo "3. Testing configuration..."
if nginx -t 2>&1; then
    echo "✓ Config valid"
else
    echo "✗ Config invalid!"
    exit 1
fi
echo ""

# 4. Full restart (not reload)
echo "4. Restarting nginx (full restart)..."
systemctl restart nginx
sleep 2
echo "✓ Nginx restarted"
echo ""

# 5. Check status
echo "5. Checking nginx status..."
systemctl status nginx --no-pager | head -10
echo ""

# 6. Test
echo "6. Testing connection..."
sleep 1
curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
echo ""

# 7. Check access log
echo "7. Checking access log..."
tail -3 /var/log/nginx/od_emoment_tech_access.log 2>/dev/null || echo "No access log entries yet"
echo ""

echo "=========================================="
echo "If still 404, check:"
echo "  sudo nginx -T 2>/dev/null | grep -A 20 'server_name od.emoment.tech'"
echo "  sudo tail -20 /var/log/nginx/error.log"
echo "=========================================="

