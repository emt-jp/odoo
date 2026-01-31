# Quick Setup Guide - After DNS Update

## ✅ Status
- DNS record updated ✓
- DNS resolving through Cloudflare ✓
- SSL certificates ready ✓
- Nginx config ready ✓

## 🚀 Complete Setup (Run these commands)

```bash
# 1. Install nginx configuration and SSL certificates
sudo ./setup_nginx_ssl.sh

# 2. Allow HTTP and HTTPS through firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. Restart nginx to apply changes
sudo systemctl restart nginx

# 4. Verify everything is working
./verify_nginx_ssl_setup.sh
```

## ✅ Test Your Setup

After running the commands above:

```bash
# Test HTTPS connection
curl -I https://od.emoment.tech

# Should return HTTP 200 or 302 (redirect to login)
# If you see SSL errors, check Cloudflare SSL mode is set to "Full"
```

## 🔍 Verify Cloudflare Settings

1. **SSL/TLS Mode**: Must be "Full" or "Full (strict)"
   - Go to Cloudflare Dashboard → SSL/TLS → Overview
   - Set SSL/TLS encryption mode to "Full"

2. **DNS Record**: Should show orange cloud (proxied)
   - Go to Cloudflare Dashboard → DNS → Records
   - `od.emoment.tech` A record should have orange cloud icon

3. **Check DNS Propagation**:
   ```bash
   dig od.emoment.tech +short
   # Should show Cloudflare IPs (not your server IP)
   ```

## 🐛 Troubleshooting

### If HTTPS doesn't work:

1. **Check nginx is running:**
   ```bash
   sudo systemctl status nginx
   ```

2. **Check nginx config:**
   ```bash
   sudo nginx -t
   ```

3. **Check Odoo is accessible locally:**
   ```bash
   curl http://localhost:8069/web/health
   ```

4. **Check firewall:**
   ```bash
   sudo ufw status
   ```

5. **Check Cloudflare SSL mode:**
   - Must be "Full" (not "Flexible" or "Off")
   - Cloudflare → SSL/TLS → Overview

### Common Issues:

- **502 Bad Gateway**: Odoo container not running → `docker-compose up -d`
- **SSL errors**: Cloudflare SSL mode wrong → Set to "Full"
- **Connection refused**: Firewall blocking → `sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`

## 📝 Your Server Info

- **Server IP**: 46.250.252.111 (IPv4)
- **Domain**: od.emoment.tech
- **Odoo Port**: 8069 (internal)
- **Longpolling Port**: 8072 (internal)

## ✅ Expected Result

After setup, visiting `https://od.emoment.tech` should:
1. Redirect from HTTP to HTTPS automatically
2. Show Odoo login page
3. Use valid SSL certificate (Cloudflare Origin Certificate)

