# Fix Nginx Configuration Error

## Problem
Nginx is trying to include `/etc/nginx/sites-enabled/odoo` which doesn't exist, causing nginx to fail.

## Solution

Run the fix script:
```bash
sudo ./fix_nginx_config.sh
```

This will:
1. Comment out the problematic include line
2. Test the nginx configuration
3. Verify everything works

## Alternative Manual Fix

If you prefer to fix it manually:

```bash
# 1. Edit nginx.conf
sudo nano /etc/nginx/nginx.conf

# 2. Find the line that says:
#    include /etc/nginx/sites-enabled/odoo;

# 3. Comment it out by adding # at the beginning:
#    # include /etc/nginx/sites-enabled/odoo;

# 4. Save and test
sudo nginx -t

# 5. If test passes, restart nginx
sudo systemctl restart nginx
```

## Why This Happens

The nginx.conf file includes configurations from `sites-enabled/` directory, but we're using `conf.d/` directory instead (which is the standard for CentOS/RHEL systems). The config in `conf.d/` is already loaded automatically, so we don't need the `sites-enabled/odoo` include.

## After Fixing

Once nginx starts successfully:
1. Test HTTPS: `curl -I https://od.emoment.tech`
2. Verify setup: `./verify_nginx_ssl_setup.sh`

