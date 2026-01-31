#!/bin/bash

set -e

echo "========================================="
echo "Applying nginx configuration for odoo.emoment.tech"
echo "========================================="
echo ""

# Must be run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo ./apply_odoo_nginx.sh"
    exit 1
fi

# Backup current configuration
echo "[1/6] Creating backup..."
BACKUP_FILE="/etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/conf.d/nginx.conf "$BACKUP_FILE"
echo "✓ Backup created: $BACKUP_FILE"

# Copy new configuration
echo ""
echo "[2/6] Applying new configuration..."
cp /home/as/ws/odoo/nginx_odoo_emoment_tech.conf /etc/nginx/conf.d/nginx.conf
echo "✓ Configuration copied"

# Show what changed
echo ""
echo "[3/6] Configuration changes:"
echo "  Domain: od.emoment.tech → odoo.emoment.tech"
echo "  SSL Certificate: /etc/nginx/ssl/emoment.tech.pem (covers all subdomains)"
echo "  SSL Key: /etc/nginx/ssl/emoment.tech.key"

# Verify SSL certificates exist
echo ""
echo "[4/6] Verifying SSL certificates..."
if [ -f /etc/nginx/ssl/emoment.tech.pem ] && [ -f /etc/nginx/ssl/emoment.tech.key ]; then
    echo "✓ SSL certificates found"
    openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -subject -dates 2>/dev/null || echo "  (could not parse certificate details)"
else
    echo "✗ ERROR: SSL certificates not found!"
    echo "  Restoring backup..."
    cp "$BACKUP_FILE" /etc/nginx/conf.d/nginx.conf
    exit 1
fi

# Test nginx configuration
echo ""
echo "[5/6] Testing nginx configuration..."
if nginx -t; then
    echo "✓ Configuration test passed"
else
    echo ""
    echo "✗ Configuration test FAILED!"
    echo "  Restoring backup..."
    cp "$BACKUP_FILE" /etc/nginx/conf.d/nginx.conf
    exit 1
fi

# Reload nginx
echo ""
echo "[6/6] Reloading nginx..."
systemctl reload nginx

if [ $? -eq 0 ]; then
    echo "✓ Nginx reloaded successfully"
else
    echo "✗ Failed to reload nginx"
    echo "  Restoring backup..."
    cp "$BACKUP_FILE" /etc/nginx/conf.d/nginx.conf
    systemctl reload nginx
    exit 1
fi

echo ""
echo "========================================="
echo "✓ SUCCESS!"
echo "========================================="
echo ""
echo "Domain updated: od.emoment.tech → odoo.emoment.tech"
echo ""
echo "Verification:"
echo "  • Check status: systemctl status nginx"
echo "  • View config: cat /etc/nginx/conf.d/nginx.conf"
echo "  • Test locally: curl -I https://odoo.emoment.tech"
echo "  • Check logs: tail -f /var/log/nginx/access.log"
echo ""
echo "Don't forget to:"
echo "  1. Update DNS: Add/update A record for odoo.emoment.tech"
echo "  2. Update Cloudflare: Ensure odoo subdomain is proxied"
echo ""
