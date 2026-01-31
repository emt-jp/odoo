# Fix Nginx 404 Error

## Problem
Getting 404 Not Found when accessing `https://od.emoment.tech`

## Root Cause
The nginx `map` variables (`$upstream_port` and `$websocket_port`) didn't have default values. When the Host header doesn't match exactly, these variables become empty, causing `proxy_pass` to fail with an invalid URL like `http://127.0.0.1:` (empty port).

## Solution

### Option 1: Run the fix script (Recommended)
```bash
sudo ./fix_nginx_map_default.sh
sudo systemctl restart nginx
```

### Option 2: Manual fix
```bash
# 1. Copy the updated config
sudo cp ops/nginx/conf.d/od_emoment_tech.conf /etc/nginx/conf.d/

# 2. Test configuration
sudo nginx -t

# 3. Restart nginx
sudo systemctl restart nginx
```

## What Was Fixed

Added default values to the map blocks:
- `default 8069;` for `$upstream_port` (Odoo web port)
- `default 8072;` for `$websocket_port` (Odoo longpolling port)

This ensures that even if the Host header doesn't match exactly, nginx will still proxy to Odoo instead of failing.

## Verify Fix

After applying the fix:
```bash
# Test HTTPS connection
curl -I https://od.emoment.tech

# Should return HTTP 200 or 302 (not 404)
```

## Check Logs

If still having issues:
```bash
sudo ./diagnose_nginx_404.sh
```

This will show:
- Error logs
- Access logs  
- Which server block is matching
- If Odoo is accessible

