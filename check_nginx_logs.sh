#!/bin/bash
# Check nginx logs and diagnose 404 errors
# Run with: sudo ./check_nginx_logs.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "Nginx Logs & Configuration Check"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# 1. Check nginx status
echo -e "${BLUE}1. Nginx Service Status${NC}"
systemctl status nginx --no-pager | head -10
echo ""

# 2. Check nginx configuration
echo -e "${BLUE}2. Testing Nginx Configuration${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}✗ Configuration has errors${NC}"
fi
echo ""

# 3. Check error logs
echo -e "${BLUE}3. Recent Nginx Error Logs${NC}"
if [ -f /var/log/nginx/error.log ]; then
    echo "Last 30 lines of error.log:"
    tail -30 /var/log/nginx/error.log
else
    echo "Checking journalctl..."
    journalctl -u nginx --no-pager -n 30 | tail -30
fi
echo ""

# 4. Check access logs
echo -e "${BLUE}4. Recent Nginx Access Logs${NC}"
if [ -f /var/log/nginx/access.log ]; then
    echo "Last 20 lines of access.log:"
    tail -20 /var/log/nginx/access.log
else
    echo "No access.log found, checking for other log files..."
    ls -la /var/log/nginx/ 2>/dev/null || echo "No nginx log directory found"
fi
echo ""

# 5. Check configuration file
echo -e "${BLUE}5. Checking Nginx Configuration File${NC}"
if [ -f /etc/nginx/conf.d/od_emoment_tech.conf ]; then
    echo "Configuration file exists:"
    cat /etc/nginx/conf.d/od_emoment_tech.conf | head -40
else
    echo -e "${RED}✗ Configuration file not found${NC}"
fi
echo ""

# 6. Check if Odoo is accessible
echo -e "${BLUE}6. Testing Odoo Connection${NC}"
if curl -s http://localhost:8069/web/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Odoo is accessible on localhost:8069${NC}"
    curl -I http://localhost:8069/web/health 2>&1 | head -5
else
    echo -e "${RED}✗ Odoo is not accessible on localhost:8069${NC}"
    echo "Check if Docker containers are running: docker-compose ps"
fi
echo ""

# 7. Check ports
echo -e "${BLUE}7. Checking Listening Ports${NC}"
netstat -tln 2>/dev/null | grep -E ":80 |:443 |:8069 |:8072 " || ss -tln 2>/dev/null | grep -E ":80 |:443 |:8069 |:8072 "
echo ""

# 8. Test nginx proxy
echo -e "${BLUE}8. Testing Nginx Proxy to Odoo${NC}"
if curl -s -H "Host: od.emoment.tech" http://localhost/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx can proxy to Odoo${NC}"
    curl -I -H "Host: od.emoment.tech" http://localhost/ 2>&1 | head -10
else
    echo -e "${RED}✗ Nginx cannot proxy to Odoo${NC}"
    echo "Testing direct connection..."
    curl -I http://127.0.0.1:8069 2>&1 | head -5
fi
echo ""

echo -e "${GREEN}=========================================="
echo "Diagnostics Complete"
echo "==========================================${NC}"

