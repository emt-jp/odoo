#!/bin/bash
# Remove unused nginx config files from system
# Run with: sudo ./cleanup_nginx_configs.sh

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

echo "=========================================="
echo "Cleaning up unused nginx configs"
echo "=========================================="
echo ""

# Backup directory
BACKUP_DIR="/etc/nginx/conf.d/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Files to remove/backup
FILES_TO_REMOVE=(
    "/etc/nginx/conf.d/tokyodrivingclub_nginx.conf"
    "/etc/nginx/conf.d/nihonrice_nginx.conf"
    "/etc/nginx/conf.d/emoment_io_nginx.conf"
)

echo "Backing up and removing unused config files..."
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        echo "  Backing up: $(basename $file)"
        cp "$file" "$BACKUP_DIR/"
        rm "$file"
        echo "    ✓ Removed"
    else
        echo "  $(basename $file) - not found, skipping"
    fi
done

echo ""
echo "Testing nginx configuration..."
if nginx -t; then
    echo "✓ Configuration is valid"
    echo ""
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded"
else
    echo "✗ Configuration test failed!"
    echo "Restoring backups..."
    cp "$BACKUP_DIR"/* /etc/nginx/conf.d/ 2>/dev/null || true
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Cleanup Complete!"
echo "=========================================="
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo "Remaining config files:"
ls -1 /etc/nginx/conf.d/*.conf 2>/dev/null | xargs -I {} basename {} | grep -v backup
echo ""
echo "Testing connection..."
sleep 1
RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/ 2>&1)
echo "Response code: $RESPONSE"
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "303" ] || [ "$RESPONSE" = "302" ]; then
    echo "✓ SUCCESS! Nginx is now working correctly"
else
    echo "⚠ Still getting $RESPONSE - may need further investigation"
fi

