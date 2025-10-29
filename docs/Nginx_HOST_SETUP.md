# Nginx Host Setup Guide

This guide explains how to configure Nginx on the VPS host system to proxy traffic to the Odoo Docker container.

## Overview

- **Nginx** runs on the VPS host (not in Docker)
- **Odoo** runs in Docker and is accessible only via `localhost:8069` on the host
- Traffic flow: `Internet → VPS:80 → Nginx (host) → 127.0.0.1:8069 → Odoo (Docker)`

## Installation

### 1. Install Nginx on the VPS Host

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
# or
sudo dnf install nginx -y
```

### 2. Configure Nginx

Create a new configuration file for Odoo:

```bash
sudo nano /etc/nginx/sites-available/odoo
```

**For Ubuntu/Debian:**
```nginx
# Upstream servers
upstream odoo {
    server 127.0.0.1:8069;
}

upstream odoochat {
    server 127.0.0.1:8072;
}

# HTTP to HTTPS redirect (recommended for production)
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.sin.com;
    
    # SSL Configuration (Let's Encrypt recommended)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Logging
    access_log /var/log/nginx/odoo_access.log;
    error_log /var/log/nginx/odoo_error.log;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    
    # Increase client body size for file uploads
    client_max_body_size 100M;
    
    # Proxy settings
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    
    # Long polling (WebSocket-like)
    location /longpolling {
        proxy_pass http://odoochat;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Web interface
    location / {
        proxy_pass http://odoo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
    
    # Health check
    location /web/health {
        proxy_pass http://odoo;
        access_log off;
    }
    
    # API rate limiting
    location /web/dataset/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://odoo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Login rate limiting
    location /web/session/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http                   proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**For CentOS/RHEL**, use `/etc/nginx/conf.d/odoo.conf` instead of `/etc/nginx/sites-available/odoo`.

### 3. Enable and Start Nginx

**Ubuntu/Debian:**
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl restart nginx
```

**CentOS/RHEL:**
```bash
# Test configuration
sudo nginx -t

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### 4. SSL Certificate Setup (Recommended)

Use Let's Encrypt for free SSL certificates:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is set up automatically
```

### 5. Firewall Configuration

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Or for firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Testing

1. **Check Nginx is running:**
   ```bash
   sudo systemctl status nginx
   ```

2. **Test your domain:**
   ```bash
   curl -I https://your-domain.com
   ```

3. **Check logs:**
   ```bash
   # Access logs
   sudo tail -f /var/log/nginx/odoo_access.log
   
   # Error logs
   sudo tail -f /var/log/nginx/odoo_error.log
   ```

## Troubleshooting

### Odoo shows "Internal Server Error"
- Check if Odoo is running: `docker-compose ps`
- Check Odoo logs: `docker-compose logs odoo`
- Verify nginx can reach Odoo: `curl http://127.0.0.1:8069`

### 502 Bad Gateway
- Odoo container might not be running
- Check firewall rules
- Verify port binding: `sudo netstat -tlnp | grep 8069`

### SSL Certificate Issues
- Renew certificate: `sudo certbot renew`
- Check certificate validity: `sudo certbot certificates`

## Security Recommendations

1. **Regular Updates:**
   ```bash
   sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
   sudo yum update -y                      # CentOS/RHEL
   ```

2. **Disable Default Site:**
   ```bash
   sudo rm /etc/nginx/sites-enabled/default
   ```

3. **Enable Security Modules:**
   - Install ModSecurity for WAF
   - Configure fail2ban for brute-force protection

4. **Rate Limiting:**
   - Already configured in the nginx config above
   - Adjust limits based on your traffic

## Quick Reference

| Component | Location |
|-----------|----------|
| Nginx config | `/etc/nginx/sites-available/odoo` (Ubuntu/Debian)<br>`/etc/nginx/conf.d/odoo.conf` (CentOS/RHEL) |
| Access logs | `/var/log/nginx/odoo_access.log` |
| Error logs | `/var/log/nginx/odoo_error.log` |
| SSL certs | `/etc/letsencrypt/live/your-domain.com/` |
| Odoo URL | `http://127.0.0.1:8069` (internal) |


