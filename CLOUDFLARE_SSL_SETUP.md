# Nginx Configuration Update: od.emoment.tech → odoo.emoment.tech

## Overview
This guide will help you:
1. Change your nginx domain from `od.emoment.tech` to `odoo.emoment.tech`
2. Install Cloudflare Origin SSL certificates

## Step 1: Generate Cloudflare Origin SSL Certificates

1. Log in to your **Cloudflare Dashboard** (https://dash.cloudflare.com)
2. Select your domain `emoment.tech`
3. Navigate to **SSL/TLS** → **Origin Server**
4. Click **Create Certificate**
5. Configure the certificate:
   - **Private key type**: RSA (2048)
   - **Hostnames**: Add `odoo.emoment.tech` and `*.emoment.tech`
   - **Certificate Validity**: 15 years (recommended)
6. Click **Create**
7. **Save both files**:
   - **Origin Certificate** → Save as `odoo.emoment.tech.pem`
   - **Private Key** → Save as `odoo.emoment.tech.key`

⚠️ **Important**: Save these files immediately. You cannot retrieve the private key later!

## Step 2: Install SSL Certificates

Run the interactive setup script:

```bash
cd ~/ws/odoo
./setup_cloudflare_ssl.sh
```

Or manually install:

```bash
# Copy your certificate files to /etc/nginx/ssl/
sudo cp /path/to/odoo.emoment.tech.pem /etc/nginx/ssl/
sudo cp /path/to/odoo.emoment.tech.key /etc/nginx/ssl/

# Set proper permissions
sudo chmod 644 /etc/nginx/ssl/odoo.emoment.tech.pem
sudo chmod 600 /etc/nginx/ssl/odoo.emoment.tech.key
```

## Step 3: Apply Nginx Configuration

Run the setup script:

```bash
cd ~/ws/odoo
./setup_odoo_nginx.sh
```

Or manually apply:

```bash
# Backup current config
sudo cp /etc/nginx/conf.d/nginx.conf /etc/nginx/conf.d/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# Copy new config
sudo cp ~/ws/odoo/nginx_odoo_emoment_tech.conf /etc/nginx/conf.d/nginx.conf

# Test configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

## Step 4: Configure Cloudflare DNS

1. In Cloudflare Dashboard, go to **DNS** → **Records**
2. Add/Update A record:
   - **Type**: A
   - **Name**: odoo
   - **IPv4 address**: Your server IP
   - **Proxy status**: Proxied (orange cloud)
   - **TTL**: Auto

## Step 5: Set Cloudflare SSL/TLS Mode

1. In Cloudflare Dashboard, go to **SSL/TLS** → **Overview**
2. Set encryption mode to **Full (strict)**
   - This ensures end-to-end encryption between Cloudflare and your origin server

## Verification

Test your setup:

```bash
# Check nginx status
sudo systemctl status nginx

# Check if nginx is listening on 443
sudo netstat -tlnp | grep :443

# Test SSL from command line
curl -I https://odoo.emoment.tech

# Check nginx logs if needed
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Files Created

- `nginx_odoo_emoment_tech.conf` - New nginx configuration
- `setup_cloudflare_ssl.sh` - SSL certificate installation script
- `setup_odoo_nginx.sh` - Nginx configuration deployment script
- `CLOUDFLARE_SSL_SETUP.md` - This guide

## Rollback

If something goes wrong:

```bash
# Find your backup
ls -lt /etc/nginx/conf.d/nginx.conf.backup.*

# Restore the backup
sudo cp /etc/nginx/conf.d/nginx.conf.backup.YYYYMMDD_HHMMSS /etc/nginx/conf.d/nginx.conf

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## Troubleshooting

### SSL Certificate Error
- Verify certificate files exist: `ls -l /etc/nginx/ssl/odoo.emoment.tech.*`
- Check file permissions (pem: 644, key: 600)
- Verify certificate validity: `openssl x509 -in /etc/nginx/ssl/odoo.emoment.tech.pem -text -noout`

### 502 Bad Gateway
- Check if Odoo is running: `sudo systemctl status odoo`
- Verify Odoo is listening on ports 8069 and 8072: `netstat -tlnp | grep -E '8069|8072'`

### DNS Not Resolving
- Check DNS propagation: `dig odoo.emoment.tech`
- Wait a few minutes for DNS to propagate (usually instant with Cloudflare)

## Notes

- The current certificate at `/etc/nginx/ssl/emoment.tech.pem` will remain unchanged
- The old domain `od.emoment.tech` will no longer work after this change
- Make sure to update any links or bookmarks to use `odoo.emoment.tech`
