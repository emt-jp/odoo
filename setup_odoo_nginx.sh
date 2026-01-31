#!/bin/bash

# Script to setup nginx for odoo.emoment.tech with Cloudflare SSL

echo "Setting up nginx configuration for odoo.emoment.tech..."

# Backup current config
echo "Creating backup..."
sudo cp /etc/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# Copy new configuration
echo "Copying new configuration..."
sudo cp /home/as/ws/odoo/nginx_odoo_emoment_tech.conf /etc/nginx/conf.d/nginx.conf

# Test nginx configuration
echo "Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "Configuration test passed!"
    echo "Reloading nginx..."
    sudo systemctl reload nginx
    echo "Done! odoo.emoment.tech is now configured."
else
    echo "Configuration test failed! Please check the errors above."
    echo "Restoring backup..."
    sudo cp /etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/conf.d/nginx.conf
fi
