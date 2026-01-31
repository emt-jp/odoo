#!/bin/bash
# Create minimal test server block - run with sudo
# Usage: sudo ./minimal_test_server.sh

set -e

CONFIG="/etc/nginx/conf.d/od_emoment_tech.conf"
BACKUP="${CONFIG}.minimal_test_backup"

echo "=========================================="
echo "Minimal Test Server Block"
echo "=========================================="
echo ""

# Backup
cp "$CONFIG" "$BACKUP"

# Create minimal config
cat > "$CONFIG" << 'EOF'
server {
    listen 443 ssl http2 default_server;
    server_name _;
    
    ssl_certificate /etc/nginx/ssl/emoment.tech.pem;
    ssl_certificate_key /etc/nginx/ssl/emoment.tech.key;
    
    location / {
        return 200 "MINIMAL_SERVER_BLOCK_WORKING\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Test
if nginx -t 2>&1; then
    echo "✓ Config valid, reloading..."
    systemctl reload nginx
    sleep 1
    
    echo "Testing..."
    RESPONSE=$(curl -s -k https://127.0.0.1/)
    if echo "$RESPONSE" | grep -q "MINIMAL_SERVER_BLOCK_WORKING"; then
        echo "✓✓✓ MINIMAL SERVER BLOCK WORKS!"
        echo "Response: $RESPONSE"
        echo ""
        echo "This means the server block CAN work. The issue is with our config."
    else
        echo "✗ Even minimal server block doesn't work"
        echo "Got: $RESPONSE"
        echo ""
        echo "This means there's something fundamentally wrong with"
        echo "how nginx is configured or how requests are being handled."
    fi
else
    echo "✗ Config invalid!"
fi

# Restore
mv "$BACKUP" "$CONFIG"
systemctl reload nginx

echo ""
echo "=========================================="

