#!/bin/bash
# Apply nginx fix and verify
# Run with: sudo ./apply_nginx_fix.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SOURCE="${SCRIPT_DIR}/ops/nginx/conf.d/od_emoment_tech.conf"
CONFIG_TARGET="/etc/nginx/conf.d/od_emoment_tech.conf"

echo "=========================================="
echo "Apply Nginx Configuration Fix"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# 1. Check source file
echo -e "${BLUE}1. Checking source configuration...${NC}"
if [ ! -f "$CONFIG_SOURCE" ]; then
    echo -e "${RED}✗ Source config not found: $CONFIG_SOURCE${NC}"
    exit 1
fi

if grep -q "default 8069" "$CONFIG_SOURCE"; then
    echo -e "${GREEN}✓ Source config has default values${NC}"
else
    echo -e "${RED}✗ Source config missing default values${NC}"
    exit 1
fi
echo ""

# 2. Backup existing config
echo -e "${BLUE}2. Backing up existing config...${NC}"
if [ -f "$CONFIG_TARGET" ]; then
    cp "$CONFIG_TARGET" "${CONFIG_TARGET}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ Backup created${NC}"
else
    echo "No existing config to backup"
fi
echo ""

# 3. Copy new config
echo -e "${BLUE}3. Copying updated configuration...${NC}"
cp "$CONFIG_SOURCE" "$CONFIG_TARGET"
chmod 644 "$CONFIG_TARGET"
chown root:root "$CONFIG_TARGET"
echo -e "${GREEN}✓ Configuration copied${NC}"
echo ""

# 4. Verify config has defaults
echo -e "${BLUE}4. Verifying configuration...${NC}"
if grep -q "default 8069" "$CONFIG_TARGET"; then
    echo -e "${GREEN}✓ Config has default 8069${NC}"
else
    echo -e "${RED}✗ Config missing default 8069${NC}"
    exit 1
fi

if grep -q "default 8072" "$CONFIG_TARGET"; then
    echo -e "${GREEN}✓ Config has default 8072${NC}"
else
    echo -e "${RED}✗ Config missing default 8072${NC}"
    exit 1
fi
echo ""

# 5. Test nginx configuration
echo -e "${BLUE}5. Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}✗ Configuration test failed${NC}"
    echo "Restoring backup..."
    cp "${CONFIG_TARGET}.backup."* "$CONFIG_TARGET" 2>/dev/null || true
    exit 1
fi
echo ""

# 6. Check for default server blocks that might interfere
echo -e "${BLUE}6. Checking for interfering server blocks...${NC}"
DEFAULT_SERVERS=$(grep -r "listen.*443.*default_server" /etc/nginx/ 2>/dev/null | grep -v "$CONFIG_TARGET" | head -3)
if [ -n "$DEFAULT_SERVERS" ]; then
    echo -e "${YELLOW}⚠ Found default_server blocks that might interfere:${NC}"
    echo "$DEFAULT_SERVERS"
    echo ""
    echo "Consider commenting them out or ensuring your config has higher priority"
else
    echo -e "${GREEN}✓ No interfering default_server blocks found${NC}"
fi
echo ""

# 7. Restart nginx
echo -e "${BLUE}7. Restarting nginx...${NC}"
if systemctl restart nginx; then
    echo -e "${GREEN}✓ Nginx restarted successfully${NC}"
else
    echo -e "${RED}✗ Failed to restart nginx${NC}"
    systemctl status nginx --no-pager | head -10
    exit 1
fi
echo ""

# 8. Wait a moment and test
echo -e "${BLUE}8. Testing configuration...${NC}"
sleep 2

# Test local connection
if curl -s -H "Host: od.emoment.tech" http://127.0.0.1/web/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Local proxy test passed${NC}"
    curl -I -H "Host: od.emoment.tech" http://127.0.0.1/web/health 2>&1 | head -3
else
    echo -e "${YELLOW}⚠ Local proxy test failed (might be HTTPS only)${NC}"
fi
echo ""

echo -e "${GREEN}=========================================="
echo "✅ Fix Applied Successfully!"
echo "==========================================${NC}"
echo ""
echo "Test your site:"
echo "  curl -I https://od.emoment.tech"
echo ""
echo "If still getting 404, check logs:"
echo "  sudo tail -50 /var/log/nginx/error.log"
echo "  sudo ./diagnose_nginx_404.sh"
echo ""

