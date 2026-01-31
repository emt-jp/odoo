#!/bin/bash
# Setup Nginx and SSL certificates to match remote server configuration
# Run with: sudo ./setup_nginx_ssl.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Nginx & SSL Setup for od.emoment.tech"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# 1. Copy SSL certificates
echo -e "${BLUE}Step 1: Installing SSL certificates...${NC}"
mkdir -p /etc/nginx/ssl
cp "${SCRIPT_DIR}/ops/ssl/emoment.tech.pem" /etc/nginx/ssl/
cp "${SCRIPT_DIR}/ops/ssl/emoment.tech.key" /etc/nginx/ssl/
chmod 644 /etc/nginx/ssl/emoment.tech.pem
chmod 600 /etc/nginx/ssl/emoment.tech.key
chown root:root /etc/nginx/ssl/emoment.tech.*

echo -e "${GREEN}✓ SSL certificates installed${NC}"

# 2. Copy nginx configuration
echo ""
echo -e "${BLUE}Step 2: Installing Nginx configuration...${NC}"
cp "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/od_emoment_tech.conf
chown root:root /etc/nginx/conf.d/od_emoment_tech.conf

echo -e "${GREEN}✓ Nginx configuration installed${NC}"

# 3. Test nginx configuration
echo ""
echo -e "${BLUE}Step 3: Testing Nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed!${NC}"
    exit 1
fi

# 4. Verify SSL certificate
echo ""
echo -e "${BLUE}Step 4: Verifying SSL certificate...${NC}"
if openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -text > /dev/null 2>&1; then
    CERT_INFO=$(openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -text | grep -E "Subject:|Issuer:|Not After" | head -3)
    echo -e "${GREEN}✓ SSL certificate is valid${NC}"
    echo "$CERT_INFO" | sed 's/^/  /'
    
    # Check expiration
    EXPIRY=$(openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -enddate | cut -d= -f2)
    echo -e "${GREEN}  Certificate expires: ${EXPIRY}${NC}"
else
    echo -e "${RED}✗ SSL certificate verification failed!${NC}"
    exit 1
fi

# 5. Check if Odoo is running on expected ports
echo ""
echo -e "${BLUE}Step 5: Verifying Odoo ports...${NC}"
if netstat -tln 2>/dev/null | grep -q ":8069 "; then
    echo -e "${GREEN}✓ Odoo is running on port 8069${NC}"
else
    echo -e "${YELLOW}⚠ Odoo is not running on port 8069${NC}"
    echo "  Make sure Docker containers are started: docker-compose up -d"
fi

if netstat -tln 2>/dev/null | grep -q ":8072 "; then
    echo -e "${GREEN}✓ Odoo longpolling is running on port 8072${NC}"
else
    echo -e "${YELLOW}⚠ Odoo longpolling is not running on port 8072${NC}"
fi

# 6. Check firewall
echo ""
echo -e "${BLUE}Step 6: Checking firewall...${NC}"
if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "80/tcp.*ALLOW" && ufw status | grep -q "443/tcp.*ALLOW"; then
        echo -e "${GREEN}✓ Firewall allows HTTP (80) and HTTPS (443)${NC}"
    else
        echo -e "${YELLOW}⚠ Firewall may need configuration:${NC}"
        echo "  sudo ufw allow 80/tcp"
        echo "  sudo ufw allow 443/tcp"
    fi
elif command -v firewall-cmd >/dev/null 2>&1; then
    if firewall-cmd --list-services | grep -q http && firewall-cmd --list-services | grep -q https; then
        echo -e "${GREEN}✓ Firewall allows HTTP and HTTPS${NC}"
    else
        echo -e "${YELLOW}⚠ Firewall may need configuration:${NC}"
        echo "  sudo firewall-cmd --permanent --add-service=http"
        echo "  sudo firewall-cmd --permanent --add-service=https"
        echo "  sudo firewall-cmd --reload"
    fi
else
    echo -e "${YELLOW}⚠ Firewall tool not found, please verify manually${NC}"
fi

# 7. Summary
echo ""
echo -e "${GREEN}=========================================="
echo "✅ Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Configuration files:"
echo "  SSL Certificate: /etc/nginx/ssl/emoment.tech.pem"
echo "  SSL Key: /etc/nginx/ssl/emoment.tech.key"
echo "  Nginx Config: /etc/nginx/conf.d/od_emoment_tech.conf"
echo ""
echo "Next steps:"
echo "1. Review the configuration:"
echo "   sudo nano /etc/nginx/conf.d/od_emoment_tech.conf"
echo ""
echo "2. Reload Nginx:"
echo "   sudo systemctl reload nginx"
echo ""
echo "3. Update Cloudflare A record to point to this server's IP"
echo ""
echo "4. Test the setup:"
echo "   curl -I https://od.emoment.tech"
echo ""

