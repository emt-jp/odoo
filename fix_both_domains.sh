#!/bin/bash

# Fix to support BOTH od.emoment.tech and odoo.emoment.tech

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo ./fix_both_domains.sh"
    exit 1
fi

echo "========================================="
echo "Adding both domains to nginx config"
echo "========================================="
echo ""

# Backup
echo "[1] Creating backup..."
cp /etc/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created"
echo ""

# Update server_name to include both domains
echo "[2] Updating server_name to include both od and odoo..."
sed -i 's/server_name odoo\.emoment\.tech _;/server_name od.emoment.tech odoo.emoment.tech _;/' /etc/nginx/conf.d/nginx.conf
sed -i 's/server_name odoo\.emoment\.tech;/server_name od.emoment.tech odoo.emoment.tech;/' /etc/nginx/conf.d/nginx.conf
echo "✓ Updated"
echo ""

# Show changes
echo "[3] New configuration:"
grep "server_name" /etc/nginx/conf.d/nginx.conf | head -5
echo ""

# Test
echo "[4] Testing nginx configuration..."
if nginx -t; then
    echo "✓ Configuration test passed"
else
    echo "✗ Configuration test failed!"
    echo "Restoring backup..."
    cp /etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/conf.d/nginx.conf
    exit 1
fi
echo ""

# Reload
echo "[5] Reloading nginx..."
systemctl reload nginx
echo "✓ Nginx reloaded"
echo ""

# Test both domains
echo "[6] Testing both domains:"
echo "  od.emoment.tech:"
curl -k -s -o /dev/null -w "    HTTP %{http_code}\n" -H "Host: od.emoment.tech" https://127.0.0.1/web

echo "  odoo.emoment.tech:"
curl -k -s -o /dev/null -w "    HTTP %{http_code}\n" -H "Host: odoo.emoment.tech" https://127.0.0.1/web

echo ""
echo "========================================="
echo "✓ Both domains now configured!"
echo "========================================="
echo ""
echo "Test publicly:"
echo "  curl -I https://od.emoment.tech/web"
echo "  curl -I https://odoo.emoment.tech/web"
echo ""
