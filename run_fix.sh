#!/bin/bash

echo "========================================="
echo "Complete Fix for odoo.emoment.tech"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo ./run_fix.sh"
    exit 1
fi

# Step 1: Show current config
echo "[STEP 1] Current nginx configuration:"
echo "--------------------------------------"
grep "server_name" /etc/nginx/conf.d/nginx.conf
echo ""

# Step 2: Backup
echo "[STEP 2] Creating backup..."
BACKUP_FILE="/etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/conf.d/nginx.conf "$BACKUP_FILE"
echo "✓ Backup: $BACKUP_FILE"
echo ""

# Step 3: Update configuration to include both domains
echo "[STEP 3] Updating configuration..."
cat > /tmp/nginx_odoo.conf << 'EOF'
# Upstream blocks for better reliability
upstream odoo_backend {
    server 127.0.0.1:8069;
}

upstream odoo_longpolling {
    server 127.0.0.1:8072;
}

server {
    listen 443 ssl http2 default_server;
    server_name od.emoment.tech odoo.emoment.tech _;

    # SSL Configuration - Using root level emoment.tech certificate (covers all subdomains)
    ssl_certificate /etc/nginx/ssl/emoment.tech.pem;
    ssl_certificate_key /etc/nginx/ssl/emoment.tech.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Standard HTTP proxying
    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket proxying
    location /websocket {
        proxy_pass http://odoo_longpolling;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name od.emoment.tech odoo.emoment.tech;

    location / {
        return 301 https://$host$request_uri;
    }
}
EOF

cp /tmp/nginx_odoo.conf /etc/nginx/conf.d/nginx.conf
echo "✓ Configuration updated to support both domains:"
grep "server_name" /etc/nginx/conf.d/nginx.conf
echo ""

# Step 4: Test configuration
echo "[STEP 4] Testing nginx configuration..."
if nginx -t 2>&1; then
    echo "✓ Configuration test passed"
else
    echo "✗ Configuration test failed!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" /etc/nginx/conf.d/nginx.conf
    exit 1
fi
echo ""

# Step 5: Reload nginx
echo "[STEP 5] Reloading nginx..."
systemctl reload nginx
if [ $? -eq 0 ]; then
    echo "✓ Nginx reloaded successfully"
else
    echo "✗ Failed to reload nginx"
    exit 1
fi
echo ""

# Step 6: Wait a moment for nginx to reload
echo "[STEP 6] Waiting for nginx to fully reload..."
sleep 2
echo ""

# Step 7: Test both domains locally
echo "[STEP 7] Testing both domains locally:"
echo "--------------------------------------"
echo -n "  od.emoment.tech: "
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: od.emoment.tech" https://127.0.0.1/web 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
    echo "✓ HTTP $HTTP_CODE"
else
    echo "✗ HTTP $HTTP_CODE"
fi

echo -n "  odoo.emoment.tech: "
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: odoo.emoment.tech" https://127.0.0.1/web 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
    echo "✓ HTTP $HTTP_CODE"
else
    echo "✗ HTTP $HTTP_CODE"
fi
echo ""

# Step 8: Test through Cloudflare
echo "[STEP 8] Testing through Cloudflare (may take a few seconds)..."
echo "--------------------------------------"
sleep 3
echo -n "  https://od.emoment.tech/web: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://od.emoment.tech/web 2>/dev/null)
echo "HTTP $HTTP_CODE"

echo -n "  https://odoo.emoment.tech/web: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://odoo.emoment.tech/web 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
    echo "✓ HTTP $HTTP_CODE - SUCCESS!"
else
    echo "⚠ HTTP $HTTP_CODE - May need Cloudflare cache purge"
fi
echo ""

echo "========================================="
echo "Fix Complete!"
echo "========================================="
echo ""
echo "If odoo.emoment.tech still shows 404:"
echo "1. Go to Cloudflare Dashboard"
echo "2. Caching → Configuration → Purge Everything"
echo "3. Wait 30 seconds and test again"
echo ""
echo "Test in browser:"
echo "  https://od.emoment.tech/web"
echo "  https://odoo.emoment.tech/web"
echo ""
