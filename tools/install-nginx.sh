#!/bin/bash
set -e

echo "=== Installing Nginx on VPS Host ==="
echo ""
echo "This script will install Nginx on the host system to proxy traffic to Odoo Docker container."
echo ""

# Update package list
echo "1. Updating package list..."
sudo apt update

# Install Nginx
echo ""
echo "2. Installing Nginx..."
sudo apt install nginx -y

# Check if Nginx is installed and running
if systemctl is-active --quiet nginx; then
    echo ""
    echo "✓ Nginx installed and running successfully!"
    echo ""
    echo "Nginx status:"
    sudo systemctl status nginx --no-pager -l
    
    echo ""
    echo "=== Next Steps ==="
    echo "1. Create the Odoo configuration file:"
    echo "   sudo nano /etc/nginx/sites-available/odoo"
    echo ""
    echo "2. Copy the configuration from: /home/as/ws/odoo/docs/Nginx_HOST_SETUP.md"
    echo ""
    echo "3. Enable the site:"
    echo "   sudo ln - Enemy /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/"
    echo ""
    echo "4. Remove default site:"
    echo "   sudo rm /etc/nginx/sites-enabled/default"
    echo ""
    echo "5. Test configuration:"
    echo "   sudo nginx -t"
    echo ""
    echo "6. Restart nginx:"
    echo "   sudo systemctl restart nginx"
    echo ""
else
    echo "Error: Nginx installation failed or service is not running"
    exit 1
fi
