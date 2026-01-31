#!/bin/bash

echo "==================================="
echo "Nginx Configuration Validation"
echo "==================================="
echo ""

# Check 1: Configuration file exists
echo "[1/7] Checking configuration file exists..."
if [ -f ~/ws/odoo/nginx_odoo_emoment_tech.conf ]; then
    echo "✓ nginx_odoo_emoment_tech.conf exists"
else
    echo "✗ Configuration file not found!"
    exit 1
fi

# Check 2: Validate basic syntax
echo ""
echo "[2/7] Validating nginx config syntax..."
if grep -q "upstream odoo_backend" ~/ws/odoo/nginx_odoo_emoment_tech.conf; then
    echo "✓ Upstream blocks present"
else
    echo "✗ Missing upstream blocks!"
fi

if grep -q "server_name odoo.emoment.tech" ~/ws/odoo/nginx_odoo_emoment_tech.conf; then
    echo "✓ Domain updated to odoo.emoment.tech"
else
    echo "✗ Domain not updated!"
fi

# Check 3: SSL certificate paths
echo ""
echo "[3/7] Checking SSL certificate paths..."
if grep -q "ssl_certificate.*odoo.emoment.tech.pem" ~/ws/odoo/nginx_odoo_emoment_tech.conf; then
    echo "✓ SSL certificate path configured"
else
    echo "✗ SSL certificate path missing!"
fi

if grep -q "ssl_certificate_key.*odoo.emoment.tech.key" ~/ws/odoo/nginx_odoo_emoment_tech.conf; then
    echo "✓ SSL key path configured"
else
    echo "✗ SSL key path missing!"
fi

# Check 4: SSL certificates exist
echo ""
echo "[4/7] Checking if SSL certificates exist..."
if [ -f /etc/nginx/ssl/odoo.emoment.tech.pem ] && [ -f /etc/nginx/ssl/odoo.emoment.tech.key ]; then
    echo "✓ SSL certificates found"
    echo "  - Certificate: /etc/nginx/ssl/odoo.emoment.tech.pem"
    echo "  - Key: /etc/nginx/ssl/odoo.emoment.tech.key"
else
    echo "⚠ SSL certificates NOT found (need to install Cloudflare certificates first)"
    echo "  Expected locations:"
    echo "  - /etc/nginx/ssl/odoo.emoment.tech.pem"
    echo "  - /etc/nginx/ssl/odoo.emoment.tech.key"
    echo ""
    echo "  Run: ./setup_cloudflare_ssl.sh to install them"
fi

# Check 5: Backend services
echo ""
echo "[5/7] Checking Odoo backend services..."
if netstat -tln 2>/dev/null | grep -q ":8069"; then
    echo "✓ Odoo main service (port 8069) is running"
else
    echo "✗ Odoo main service (port 8069) is NOT running!"
fi

if netstat -tln 2>/dev/null | grep -q ":8072"; then
    echo "✓ Odoo longpolling service (port 8072) is running"
else
    echo "✗ Odoo longpolling service (port 8072) is NOT running!"
fi

# Check 6: Nginx status
echo ""
echo "[6/7] Checking nginx service..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "✓ Nginx is running"
elif pgrep nginx > /dev/null; then
    echo "✓ Nginx is running"
else
    echo "⚠ Cannot determine nginx status (may need sudo)"
fi

# Check 7: Current configuration
echo ""
echo "[7/7] Checking current nginx configuration..."
if [ -f /etc/nginx/conf.d/nginx.conf ]; then
    if grep -q "od.emoment.tech" /etc/nginx/conf.d/nginx.conf; then
        echo "⚠ Current config still uses od.emoment.tech (not updated yet)"
    elif grep -q "odoo.emoment.tech" /etc/nginx/conf.d/nginx.conf; then
        echo "✓ Current config already uses odoo.emoment.tech"
    else
        echo "⚠ Cannot determine current domain"
    fi
else
    echo "⚠ Cannot read current nginx config (may need sudo)"
fi

echo ""
echo "==================================="
echo "Summary"
echo "==================================="
echo ""

# Summary and next steps
if [ -f /etc/nginx/ssl/odoo.emoment.tech.pem ]; then
    echo "Status: Ready to apply configuration!"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./setup_odoo_nginx.sh"
    echo "  2. Verify nginx: sudo systemctl status nginx"
    echo "  3. Test the site: curl -I https://odoo.emoment.tech"
else
    echo "Status: Need to install Cloudflare SSL certificates first"
    echo ""
    echo "Next steps:"
    echo "  1. Generate certificates in Cloudflare dashboard"
    echo "  2. Run: ./setup_cloudflare_ssl.sh"
    echo "  3. Run: ./setup_odoo_nginx.sh"
    echo ""
    echo "See CLOUDFLARE_SSL_SETUP.md for detailed instructions"
fi

echo ""
