#!/bin/bash

# Script to setup Cloudflare SSL certificates for odoo.emoment.tech

echo "Cloudflare SSL Certificate Setup"
echo "================================="
echo ""
echo "This script will help you install Cloudflare Origin SSL certificates."
echo ""
echo "Before running this script, you need to:"
echo "1. Log in to your Cloudflare dashboard"
echo "2. Go to SSL/TLS > Origin Server"
echo "3. Click 'Create Certificate'"
echo "4. Choose 'Generate private key and CSR with Cloudflare'"
echo "5. Add 'odoo.emoment.tech' to the hostnames"
echo "6. Choose certificate validity (15 years recommended)"
echo "7. Click 'Create'"
echo "8. Save the Origin Certificate and Private Key"
echo ""
read -p "Have you generated the Cloudflare Origin Certificate? (y/n): " response

if [ "$response" != "y" ]; then
    echo "Please generate the certificates first and run this script again."
    exit 1
fi

echo ""
echo "Please provide the path to your Cloudflare Origin Certificate file (.pem or .crt):"
read -p "Certificate path: " cert_path

echo "Please provide the path to your Cloudflare Private Key file (.key):"
read -p "Private key path: " key_path

if [ ! -f "$cert_path" ]; then
    echo "Error: Certificate file not found at $cert_path"
    exit 1
fi

if [ ! -f "$key_path" ]; then
    echo "Error: Private key file not found at $key_path"
    exit 1
fi

echo ""
echo "Installing certificates..."
sudo cp "$cert_path" /etc/nginx/ssl/odoo.emoment.tech.pem
sudo cp "$key_path" /etc/nginx/ssl/odoo.emoment.tech.key

echo "Setting permissions..."
sudo chmod 644 /etc/nginx/ssl/odoo.emoment.tech.pem
sudo chmod 600 /etc/nginx/ssl/odoo.emoment.tech.key

echo ""
echo "Cloudflare SSL certificates installed successfully!"
echo "Certificate: /etc/nginx/ssl/odoo.emoment.tech.pem"
echo "Private Key: /etc/nginx/ssl/odoo.emoment.tech.key"
echo ""
echo "Next steps:"
echo "1. Run ./setup_odoo_nginx.sh to apply the nginx configuration"
echo "2. Make sure DNS for odoo.emoment.tech points to this server"
echo "3. Set Cloudflare SSL/TLS encryption mode to 'Full (strict)'"
