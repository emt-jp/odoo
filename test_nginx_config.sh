#!/bin/bash

echo "Testing nginx configuration..."
echo "=============================="
echo ""

# Test the configuration with temporary cert
echo "1. Testing with existing emoment.tech certificate (temporary)..."
sudo cp ~/ws/odoo/nginx_odoo_test.conf /etc/nginx/conf.d/nginx.conf.test
sudo nginx -t -c /etc/nginx/nginx.conf 2>&1 | grep -A 10 "test"

echo ""
echo "2. Checking configuration syntax..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Nginx configuration syntax is valid!"
    echo ""
    echo "3. Current nginx status:"
    sudo systemctl status nginx --no-pager -l | head -20
    echo ""
    echo "4. Listening ports:"
    sudo netstat -tlnp | grep nginx
else
    echo ""
    echo "✗ Nginx configuration has errors!"
fi

# Clean up test file
sudo rm -f /etc/nginx/conf.d/nginx.conf.test

echo ""
echo "=============================="
echo "Test complete!"
