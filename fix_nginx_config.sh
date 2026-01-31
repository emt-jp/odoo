#!/bin/bash
# Fix nginx configuration issue
# Run with: sudo ./fix_nginx_config.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "Fixing Nginx Configuration"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if the problematic include exists
if grep -q "sites-enabled/odoo" /etc/nginx/nginx.conf; then
    echo -e "${BLUE}Found reference to sites-enabled/odoo in nginx.conf${NC}"
    
    # Check if the file exists
    if [ ! -f "/etc/nginx/sites-enabled/odoo" ]; then
        echo -e "${YELLOW}File /etc/nginx/sites-enabled/odoo does not exist${NC}"
        echo "Checking if we should comment it out or create it..."
        
        # Check if sites-enabled directory exists
        if [ ! -d "/etc/nginx/sites-enabled" ]; then
            echo "Creating sites-enabled directory..."
            mkdir -p /etc/nginx/sites-enabled
        fi
        
        # Option 1: Comment out the include line
        echo "Commenting out the problematic include line..."
        sed -i 's|include /etc/nginx/sites-enabled/odoo;|# include /etc/nginx/sites-enabled/odoo;|g' /etc/nginx/nginx.conf
        
        echo -e "${GREEN}✓ Commented out problematic include${NC}"
    fi
fi

# Also check for any other missing includes
echo ""
echo -e "${BLUE}Checking for other missing includes...${NC}"
MISSING_INCLUDES=$(grep -E "^\s*include\s+/etc/nginx/sites-enabled/" /etc/nginx/nginx.conf | while read line; do
    FILE=$(echo "$line" | sed 's/.*include\s*\([^;]*\);/\1/' | tr -d ' ')
    if [ ! -f "$FILE" ] && [ ! -L "$FILE" ]; then
        echo "$line"
    fi
done)

if [ -n "$MISSING_INCLUDES" ]; then
    echo -e "${YELLOW}Found missing includes, commenting them out...${NC}"
    echo "$MISSING_INCLUDES" | while read line; do
        FILE=$(echo "$line" | sed 's/.*include\s*\([^;]*\);/\1/' | tr -d ' ')
        echo "  Commenting: $FILE"
        sed -i "s|^\(.*include.*$FILE.*\)|# \1|g" /etc/nginx/nginx.conf
    done
fi

# Test nginx configuration
echo ""
echo -e "${BLUE}Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is now valid${NC}"
    echo ""
    echo "You can now restart nginx:"
    echo "  sudo systemctl restart nginx"
else
    echo -e "${RED}✗ Nginx configuration still has errors${NC}"
    echo "Showing error details:"
    nginx -t
    exit 1
fi

