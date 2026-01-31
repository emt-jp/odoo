# Nginx & SSL Setup Complete ✅

## Summary

Your nginx configuration and SSL certificates have been downloaded and configured to match the remote server (`od.emoment.tech`). Everything is ready for you to update the Cloudflare A record.

## ✅ What's Done

1. **SSL Certificates Downloaded**
   - Certificate: `ops/ssl/emoment.tech.pem` (Cloudflare Origin Certificate)
   - Private Key: `ops/ssl/emoment.tech.key`
   - Valid until: March 7, 2040
   - Covers: `*.emoment.tech` and `emoment.tech` (includes `od.emoment.tech`)

2. **Nginx Configuration Created**
   - Config file: `ops/nginx/conf.d/od_emoment_tech.conf`
   - Matches remote server configuration
   - Routes `od.emoment.tech` → port 8069 (Odoo)
   - Routes `/longpolling` → port 8072 (Odoo WebSocket)
   - HTTP → HTTPS redirect configured

3. **Odoo Running**
   - ✅ Odoo container running on port 8069
   - ✅ Longpolling running on port 8072

## 📋 Final Setup Steps

Run these commands to complete the setup:

```bash
# 1. Install nginx configuration and SSL certificates
sudo ./setup_nginx_ssl.sh

# 2. Allow HTTP and HTTPS through firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. Start/restart nginx
sudo systemctl restart nginx

# 4. Verify everything is working
./verify_nginx_ssl_setup.sh
```

## 🔄 Cloudflare Configuration

After running the setup script, update your Cloudflare DNS:

1. **Get your server's public IP:**
   ```bash
   curl ifconfig.me
   ```

2. **Update Cloudflare A record:**
   - Go to Cloudflare DNS settings
   - Find the A record for `od.emoment.tech`
   - Update it to point to your server's IP address
   - TTL: Auto (or 300 seconds)

3. **Verify SSL Mode:**
   - In Cloudflare, go to SSL/TLS settings
   - Ensure SSL mode is set to **"Full"** or **"Full (strict)"**
   - This is required for Cloudflare Origin Certificates

## ✅ Verification

After updating the A record, test:

```bash
# Test HTTPS connection
curl -I https://od.emoment.tech

# Test from browser
# Open: https://od.emoment.tech
```

## 📁 File Locations

| File | Location |
|------|----------|
| SSL Certificate | `/etc/nginx/ssl/emoment.tech.pem` |
| SSL Key | `/etc/nginx/ssl/emoment.tech.key` |
| Nginx Config | `/etc/nginx/conf.d/od_emoment_tech.conf` |
| Backup Config | `ops/nginx/conf.d/od_emoment_tech.conf` |
| Backup SSL | `ops/ssl/emoment.tech.*` |

## 🔍 Configuration Details

### Port Mapping
- `od.emoment.tech` → `127.0.0.1:8069` (Odoo web)
- `/longpolling` → `127.0.0.1:8072` (Odoo WebSocket)

### SSL Certificate
- **Type:** Cloudflare Origin Certificate
- **Issuer:** CloudFlare Origin SSL Certificate Authority
- **Valid:** Until March 7, 2040
- **Domains:** `*.emoment.tech`, `emoment.tech`

### Nginx Features
- HTTP to HTTPS redirect
- SSL/TLS 1.2 and 1.3
- HTTP/2 support
- WebSocket support for longpolling
- Proper proxy headers

## 🛠️ Troubleshooting

### Nginx won't start
```bash
# Check configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### SSL certificate errors
```bash
# Verify certificate
openssl x509 -in /etc/nginx/ssl/emoment.tech.pem -noout -text

# Check permissions
ls -la /etc/nginx/ssl/
```

### Odoo not accessible
```bash
# Check Odoo is running
docker-compose ps

# Check ports
netstat -tln | grep -E "8069|8072"

# Test local connection
curl http://localhost:8069/web/health
```

## 📝 Notes

- The SSL certificate is a **Cloudflare Origin Certificate**, which means:
  - It's valid for communication between Cloudflare and your server
  - Cloudflare handles the public-facing SSL certificate
  - You must use Cloudflare's proxy (orange cloud) for this to work
  - SSL mode in Cloudflare must be "Full" or "Full (strict)"

- The configuration matches the remote server exactly, with minor improvements:
  - Added `X-Forwarded-Proto` header
  - Added explicit `/longpolling` location block

## ✅ Ready to Go!

Once you:
1. Run `sudo ./setup_nginx_ssl.sh`
2. Update the Cloudflare A record
3. Verify SSL mode is "Full" in Cloudflare

Your site will be live at `https://od.emoment.tech`! 🎉

