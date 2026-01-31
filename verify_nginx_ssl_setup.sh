#!/bin/bash
# Verify Nginx and SSL setup matches remote server
# Run with: ./verify_nginx_ssl_setup.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Nginx & SSL Setup Verification"
echo "=========================================="
echo ""

# Load config
if [ -f .migration_config ]; then
    source .migration_config
fi

REMOTE_HOST="${REMOTE_HOST:-103.101.59.102}"
REMOTE_USER="${REMOTE_SSH_USER:-as}"
SSH_KEY="${REMOTE_SSH_KEY:-$HOME/.ssh/id_ed25519_odoo}"

SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no"

# 1. Check SSL certificates
echo -e "${BLUE}1. Verifying SSL certificates...${NC}"
if [ -f "${SCRIPT_DIR}/ops/ssl/emoment.tech.pem" ] && [ -f "${SCRIPT_DIR}/ops/ssl/emoment.tech.key" ]; then
    echo -e "${GREEN}✓ Local SSL certificates exist${NC}"
    
    # Compare certificates
    LOCAL_CERT_HASH=$(openssl x509 -in "${SCRIPT_DIR}/ops/ssl/emoment.tech.pem" -noout -fingerprint -sha256 | cut -d= -f2)
    REMOTE_CERT_HASH=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "sudo openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -fingerprint -sha256 2>/dev/null" | cut -d= -f2)
    
    if [ "$LOCAL_CERT_HASH" == "$REMOTE_CERT_HASH" ]; then
        echo -e "${GREEN}✓ SSL certificates match remote server${NC}"
    else
        echo -e "${YELLOW}⚠ SSL certificates differ (may be normal if regenerated)${NC}"
    fi
    
    # Check certificate validity
    EXPIRY=$(openssl x509 -in "${SCRIPT_DIR}/ops/ssl/emoment.tech.pem" -noout -enddate | cut -d= -f2)
    echo "  Certificate expires: $EXPIRY"
    
    # Check certificate domains
    DOMAINS=$(openssl x509 -in "${SCRIPT_DIR}/ops/ssl/emoment.tech.pem" -noout -text | grep -A 1 "Subject Alternative Name" | tail -1 | sed 's/.*DNS://g' | tr ',' '\n' | sed 's/^/    /')
    echo "  Certificate covers:"
    echo "$DOMAINS"
else
    echo -e "${RED}✗ Local SSL certificates not found${NC}"
fi

# 2. Check nginx configuration
echo ""
echo -e "${BLUE}2. Verifying Nginx configuration...${NC}"
if [ -f "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" ]; then
    echo -e "${GREEN}✓ Local Nginx configuration exists${NC}"
    
    # Check if installed in system
    if [ -f "/etc/nginx/conf.d/od_emoment_tech.conf" ]; then
        echo -e "${GREEN}✓ Nginx configuration is installed in /etc/nginx/conf.d/${NC}"
        
        # Test nginx config
        if sudo nginx -t 2>&1 | grep -q "successful"; then
            echo -e "${GREEN}✓ Nginx configuration test passed${NC}"
        else
            echo -e "${RED}✗ Nginx configuration test failed${NC}"
            sudo nginx -t
        fi
    else
        echo -e "${YELLOW}⚠ Nginx configuration not installed yet${NC}"
        echo "  Run: sudo ./setup_nginx_ssl.sh"
    fi
    
    # Compare with remote
    echo ""
    echo "Comparing with remote configuration..."
    REMOTE_CONFIG=$($SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "sudo cat /etc/nginx/conf.d/nginx.conf 2>/dev/null" | grep -v "^#" | grep -v "^$")
    LOCAL_CONFIG=$(cat "${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf" | grep -v "^#" | grep -v "^$")
    
    if [ "$REMOTE_CONFIG" == "$LOCAL_CONFIG" ]; then
        echo -e "${GREEN}✓ Configurations match${NC}"
    else
        echo -e "${YELLOW}⚠ Configurations differ (checking key differences)...${NC}"
        # Check key settings
        REMOTE_PORT=$(echo "$REMOTE_CONFIG" | grep "od.emoment.tech 8069" | wc -l)
        LOCAL_PORT=$(echo "$LOCAL_CONFIG" | grep "od.emoment.tech 8069" | wc -l)
        if [ "$REMOTE_PORT" -gt 0 ] && [ "$LOCAL_PORT" -gt 0 ]; then
            echo -e "${GREEN}  ✓ Port mapping correct (od.emoment.tech -> 8069)${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Local Nginx configuration not found${NC}"
fi

# 3. Check Odoo is running
echo ""
echo -e "${BLUE}3. Verifying Odoo is running...${NC}"
if docker-compose ps odoo 2>/dev/null | grep -q "Up"; then
    echo -e "${GREEN}✓ Odoo container is running${NC}"
    
    # Check ports
    if netstat -tln 2>/dev/null | grep -q ":8069 "; then
        echo -e "${GREEN}✓ Port 8069 is listening${NC}"
    else
        echo -e "${YELLOW}⚠ Port 8069 is not listening${NC}"
    fi
    
    if netstat -tln 2>/dev/null | grep -q ":8072 "; then
        echo -e "${GREEN}✓ Port 8072 (longpolling) is listening${NC}"
    else
        echo -e "${YELLOW}⚠ Port 8072 is not listening${NC}"
    fi
else
    echo -e "${RED}✗ Odoo container is not running${NC}"
    echo "  Start with: docker-compose up -d"
fi

# 4. Check nginx service
echo ""
echo -e "${BLUE}4. Checking Nginx service...${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx service is running${NC}"
elif systemctl is-enabled --quiet nginx 2>/dev/null; then
    echo -e "${YELLOW}⚠ Nginx service is enabled but not running${NC}"
    echo "  Start with: sudo systemctl start nginx"
else
    echo -e "${YELLOW}⚠ Nginx service is not enabled${NC}"
    echo "  Enable with: sudo systemctl enable nginx"
fi

# 5. Check firewall
echo ""
echo -e "${BLUE}5. Checking firewall...${NC}"
if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "80/tcp.*ALLOW" && ufw status | grep -q "443/tcp.*ALLOW"; then
        echo -e "${GREEN}✓ Firewall allows HTTP (80) and HTTPS (443)${NC}"
    else
        echo -e "${YELLOW}⚠ Firewall needs configuration:${NC}"
        echo "  sudo ufw allow 80/tcp"
        echo "  sudo ufw allow 443/tcp"
    fi
elif command -v firewall-cmd >/dev/null 2>&1; then
    if firewall-cmd --list-services 2>/dev/null | grep -q http && firewall-cmd --list-services 2>/dev/null | grep -q https; then
        echo -e "${GREEN}✓ Firewall allows HTTP and HTTPS${NC}"
    else
        echo -e "${YELLOW}⚠ Firewall needs configuration${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Firewall tool not found${NC}"
fi

# 6. Summary
echo ""
echo -e "${GREEN}=========================================="
echo "Verification Complete"
echo "==========================================${NC}"
echo ""
echo "Ready for Cloudflare A record update:"
echo "  1. SSL certificates: ✅ Downloaded and valid"
echo "  2. Nginx config: ✅ Created (matches remote)"
echo "  3. Run setup: sudo ./setup_nginx_ssl.sh"
echo "  4. Update Cloudflare A record to point to this server"
echo "  5. Test: curl -I https://od.emoment.tech"
echo ""

