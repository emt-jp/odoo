#!/bin/bash
# Find duplicate configs - run with sudo
# Usage: sudo ./find_duplicate_configs.sh

echo "=========================================="
echo "Finding Duplicate Config Files"
echo "=========================================="
echo ""

# 1. List all config files
echo "1. All config files in conf.d:"
echo "----------------------------------------"
find /etc/nginx/conf.d/ -name "*.conf*" -type f | sort
echo ""

# 2. Find files with od.emoment.tech
echo "2. Files containing 'od.emoment.tech':"
echo "----------------------------------------"
grep -r "server_name.*od.emoment" /etc/nginx/conf.d/ 2>/dev/null | cut -d: -f1 | sort -u
echo ""

# 3. Show content of each file with od.emoment.tech
echo "3. Content of files with od.emoment.tech:"
echo "----------------------------------------"
for file in $(grep -r "server_name.*od.emoment" /etc/nginx/conf.d/ 2>/dev/null | cut -d: -f1 | sort -u); do
    echo "--- File: $file ---"
    grep -A 5 "server_name.*od.emoment" "$file" | head -10
    echo ""
done

# 4. Check for backup files
echo "4. Backup files (might be loaded):"
echo "----------------------------------------"
find /etc/nginx/conf.d/ -name "*.backup*" -o -name "*.conf.backup*" -o -name "*backup*.conf" 2>/dev/null
echo ""

# 5. Check nginx -T to see what's actually loaded
echo "5. Server blocks nginx actually sees:"
echo "----------------------------------------"
nginx -T 2>/dev/null | grep -B 3 -A 3 "server_name.*od.emoment" | head -20
echo ""

echo "=========================================="
echo "If you see backup files, remove them:"
echo "  sudo rm /etc/nginx/conf.d/*.backup*"
echo "  sudo rm /etc/nginx/conf.d/*backup*.conf"
echo "=========================================="

