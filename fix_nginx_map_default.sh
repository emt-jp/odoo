#!/bin/bash
# Fix nginx map variables by adding default values
# This prevents 404 errors when Host header doesn't match exactly

set -e

NGINX_CONF="/etc/nginx/conf.d/nginx.conf"
BACKUP_CONF="/etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "Fixing Nginx Map Default Values"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "✗ Please run as root (use sudo)"
    exit 1
fi

# Backup current config
if [ -f "$NGINX_CONF" ]; then
    echo "1. Backing up current config to: $BACKUP_CONF"
    cp "$NGINX_CONF" "$BACKUP_CONF"
    echo "   ✓ Backup created"
else
    echo "✗ Configuration file not found: $NGINX_CONF"
    exit 1
fi

# Check if default already exists
if grep -q "default 8069" "$NGINX_CONF"; then
    echo "2. Default values already exist in map blocks"
    echo "   ✓ No changes needed"
else
    echo "2. Adding default values to map blocks..."
    
    # Add default to upstream_port map
    sed -i '/^map \$host \$upstream_port {/a\    default 8069;  # Default to Odoo port' "$NGINX_CONF"
    
    # Add default to websocket_port map
    sed -i '/^map \$host \$websocket_port {/a\    default 8072;  # Default to Odoo longpolling port' "$NGINX_CONF"
    
    echo "   ✓ Default values added"
fi

# Test configuration
echo ""
echo "3. Testing nginx configuration..."
if nginx -t; then
    echo "   ✓ Configuration is valid"
else
    echo "   ✗ Configuration test failed!"
    echo "   Restoring backup..."
    cp "$BACKUP_CONF" "$NGINX_CONF"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Fix Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  sudo systemctl reload nginx"
echo "  # or"
echo "  sudo systemctl restart nginx"
echo ""
echo "Backup saved to: $BACKUP_CONF"
