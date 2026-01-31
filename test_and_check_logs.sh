#!/bin/bash
# Test and check logs - run with sudo
# Usage: sudo ./test_and_check_logs.sh

echo "=========================================="
echo "Testing and Checking Logs"
echo "=========================================="
echo ""

# 1. Make a test request
echo "1. Making test request to https://od.emoment.tech/web/health"
curl -I -k -H "Host: od.emoment.tech" https://127.0.0.1/web/health 2>&1 | head -5
echo ""

# 2. Wait a moment for logs
sleep 1

# 3. Check custom access log
echo "2. Custom access log (od_emoment_tech_access.log):"
echo "----------------------------------------"
if [ -f /var/log/nginx/od_emoment_tech_access.log ]; then
    tail -5 /var/log/nginx/od_emoment_tech_access.log
else
    echo "✗ Log file doesn't exist - server block might not be matching!"
fi
echo ""

# 4. Check main access log
echo "3. Main access log:"
echo "----------------------------------------"
tail -5 /var/log/nginx/access.log 2>/dev/null | grep -E "od.emoment|443" || tail -3 /var/log/nginx/access.log 2>/dev/null
echo ""

# 5. Check error log for warnings/errors
echo "4. Error log (warnings and errors only):"
echo "----------------------------------------"
grep -E "warn|error|failed" /var/log/nginx/od_emoment_tech_error.log 2>/dev/null | tail -10 || echo "No warnings/errors"
echo ""

# 6. Check which server blocks exist
echo "5. Server blocks on port 443:"
echo "----------------------------------------"
grep -r "listen.*443" /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "^#" | grep -v "backup"
echo ""

echo "=========================================="
echo "If custom log is empty, the server block"
echo "isn't matching. Check server_name and"
echo "ensure no other server block catches it first."
echo "=========================================="

