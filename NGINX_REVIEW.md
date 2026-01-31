# Nginx Configuration Review for Odoo

**Date**: 2025-11-26
**System**: od.emoment.tech / odoo.emoment.tech
**Nginx Version**: 1.24.0 (Ubuntu)
**Status**: ✅ OPERATIONAL with recommendations

---

## Executive Summary

✅ **Overall Status**: WORKING
⚠️ **Security**: Needs improvements
✅ **Proxy Configuration**: Functional
⚠️ **SSL/TLS**: Valid but needs optimization
⚠️ **Odoo Integration**: Needs proxy_mode enabled

---

## 1. Configuration Files Overview

### Active Configurations

| File | Purpose | Status |
|------|---------|--------|
| `/etc/nginx/nginx.conf` | Main config | ✅ Valid |
| `/etc/nginx/conf.d/nginx.conf` | Odoo proxy | ✅ Active |
| `/etc/nginx/sites-enabled/default` | Default site | ✅ Active |
| `/etc/nginx/ssl/emoment.tech.pem` | SSL cert | ✅ Valid |
| `/etc/nginx/ssl/emoment.tech.key` | SSL key | ✅ Valid |

### Backup Configurations

Multiple backups found in `/etc/nginx/conf.d/backup_20251119_171903/`:
- `emoment_io_nginx.conf`
- `tokyodrivingclub_nginx.conf`
- `nihonrice_nginx.conf`

---

## 2. Current Nginx Configuration Analysis

### Main Configuration (`/etc/nginx/nginx.conf`)

✅ **Strengths**:
- Worker processes set to `auto` (optimal)
- Worker connections: 768 (reasonable)
- Gzip enabled
- Sendfile and tcp_nopush optimized

⚠️ **Issues**:
1. **TLS 1.0 and 1.1 enabled** - These are deprecated
   ```nginx
   ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
   ```
   **Risk**: Vulnerable to known attacks (BEAST, POODLE variants)

2. **server_tokens not disabled** - Exposes Nginx version
   ```nginx
   # server_tokens off;  # <-- Commented out
   ```
   **Risk**: Information disclosure

3. **Gzip optimization disabled** - Performance not optimal
   ```nginx
   # gzip_vary on;
   # gzip_proxied any;
   # gzip_comp_level 6;
   ```

### Odoo Proxy Configuration (`/etc/nginx/conf.d/nginx.conf`)

✅ **Strengths**:
- Upstream blocks properly defined
- HTTP/2 enabled
- WebSocket support configured
- Proper proxy headers set
- Generous timeouts (300s)
- HTTP to HTTPS redirect working

⚠️ **Issues**:

1. **Duplicate upstream definitions** (line 2-8)
   ```nginx
   upstream odoo_backend {
       server 127.0.0.1:8069;
   }
   upstream odoo_longpolling {
       server 127.0.0.1:8072;
   }
   ```
   **Issue**: `odoo_backend` defined but not used (line 22 uses direct IP)

2. **default_server conflict**
   ```nginx
   listen 443 ssl http2 default_server;
   ```
   **Risk**: May conflict with sites-enabled/default on port 80

3. **Missing security headers**
   - No HSTS (Strict-Transport-Security)
   - No X-Frame-Options
   - No Content-Security-Policy
   - No X-XSS-Protection

4. **Weak SSL ciphers**
   ```nginx
   ssl_ciphers HIGH:!aNULL:!MD5;
   ```
   **Issue**: Too permissive, allows weak ciphers

5. **Missing rate limiting** - No protection against DDoS/brute force

6. **Large file uploads not optimized**
   - No client_max_body_size set
   - May fail for large Odoo attachments

7. **No access restrictions**
   - `/web/database/manager` publicly accessible
   - No IP whitelisting for admin areas

---

## 3. Critical Security Issues

### 🔴 HIGH SEVERITY

1. **Odoo Database Manager Exposed**
   - URL: `https://od.emoment.tech/web/database/manager`
   - **Risk**: Anyone can create/delete/backup databases
   - **Solution**: Restrict by IP or disable

2. **Weak TLS Configuration**
   - TLS 1.0 and 1.1 enabled
   - **Risk**: POODLE, BEAST attacks possible
   - **Solution**: Disable old TLS versions

3. **No Rate Limiting**
   - **Risk**: Brute force attacks on login
   - **Solution**: Implement rate limiting

### 🟡 MEDIUM SEVERITY

1. **Information Disclosure**
   - Nginx version exposed in headers
   - **Solution**: Enable `server_tokens off`

2. **Missing Security Headers**
   - **Risk**: Clickjacking, XSS vulnerabilities
   - **Solution**: Add security headers

3. **Odoo proxy_mode = False**
   - Located in: `/home/as/ws/odoo/ops/config/odoo.conf`
   - **Risk**: Odoo won't trust proxy headers
   - **Solution**: Set `proxy_mode = True`

### 🟢 LOW SEVERITY

1. **Gzip not optimized**
   - **Impact**: Slower page loads
   - **Solution**: Enable gzip options

2. **No access logging for specific paths**
   - **Impact**: Limited audit trail
   - **Solution**: Add detailed logging

---

## 4. SSL/TLS Configuration Review

### Certificate Information

```
Subject: CN=*.emoment.tech
Issuer: Self-signed or CA
Protocols: TLSv1, TLSv1.1, TLSv1.2, TLSv1.3
Ciphers: HIGH:!aNULL:!MD5
```

⚠️ **Issues**:
1. Allows TLS 1.0 and 1.1 (deprecated)
2. Cipher suite too permissive
3. No OCSP stapling
4. No session ticket rotation

---

## 5. Performance Issues

1. **Gzip compression not fully enabled**
   - Missing: gzip_vary, gzip_proxied, gzip_comp_level
   - **Impact**: 30-40% larger response sizes

2. **No caching headers**
   - Static assets not cached
   - **Impact**: Unnecessary server load

3. **No connection pooling optimization**
   - keepalive not configured for upstreams
   - **Impact**: More connections = more overhead

---

## 6. Testing Results

### ✅ Tests Passed

```bash
# Nginx syntax check
nginx -t
# Result: ✅ Configuration syntax is ok

# HTTP access
curl -I http://localhost
# Result: ✅ 200 OK

# Direct Odoo access
curl -I http://localhost:8069
# Result: ✅ 303 redirect to /odoo

# HTTPS proxy access
curl -k -I https://localhost/web/database/selector
# Result: ✅ HTTP/2 200 OK

# Ports listening
netstat -tlnp | grep -E "80|443"
# Result: ✅ Nginx listening on 80, 443
```

### Port Status

| Port | Service | Status |
|------|---------|--------|
| 80 | Nginx HTTP | ✅ Listening |
| 443 | Nginx HTTPS | ✅ Listening |
| 8069 | Odoo HTTP | ✅ Listening (Docker) |
| 8072 | Odoo Longpolling | ✅ Listening (Docker) |

---

## 7. Recommended Fixes

### Priority 1: Critical Security (Immediate)

#### 1.1 Restrict Database Manager Access

Create `/etc/nginx/conf.d/odoo_security.conf`:

```nginx
# Restrict database manager to specific IPs
location /web/database/manager {
    allow 127.0.0.1;           # localhost
    allow YOUR_ADMIN_IP;       # Replace with your IP
    deny all;

    proxy_pass http://127.0.0.1:8069;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

#### 1.2 Update TLS Configuration

Edit `/etc/nginx/nginx.conf`:

```nginx
# Replace line 32
ssl_protocols TLSv1.2 TLSv1.3;  # Only modern TLS

# Add after ssl_prefer_server_ciphers
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;
```

#### 1.3 Enable Odoo Proxy Mode

Edit `/home/as/ws/odoo/ops/config/odoo.conf`:

```ini
proxy_mode = True
```

Then restart Odoo:
```bash
docker restart odoo-odoo-1
```

### Priority 2: Security Headers (Within 24h)

Edit `/etc/nginx/conf.d/nginx.conf`, add inside `server` block:

```nginx
# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# CSP for Odoo
add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; frame-ancestors 'self';" always;
```

### Priority 3: Rate Limiting (Within 24h)

Edit `/etc/nginx/nginx.conf`, add in `http` block:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
```

Edit `/etc/nginx/conf.d/nginx.conf`, add:

```nginx
# Apply rate limit to login
location /web/login {
    limit_req zone=login burst=3 nodelay;
    limit_req_status 429;

    proxy_pass http://127.0.0.1:8069;
    # ... rest of proxy config
}

# Apply rate limit to xmlrpc
location /xmlrpc {
    limit_req zone=api burst=20 nodelay;

    proxy_pass http://127.0.0.1:8069;
    # ... rest of proxy config
}
```

### Priority 4: Performance Optimizations (Within 1 week)

#### 4.1 Enable Full Gzip Compression

Edit `/etc/nginx/nginx.conf`:

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 16 8k;
gzip_http_version 1.1;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/x-javascript image/svg+xml;
gzip_min_length 256;
```

#### 4.2 Increase Upload Limits

Edit `/etc/nginx/conf.d/nginx.conf`:

```nginx
# Inside server block
client_max_body_size 100M;  # Allow 100MB uploads
client_body_timeout 300s;
```

#### 4.3 Optimize Upstreams

Edit `/etc/nginx/conf.d/nginx.conf`:

```nginx
upstream odoo_backend {
    server 127.0.0.1:8069;
    keepalive 32;
}

upstream odoo_longpolling {
    server 127.0.0.1:8072;
    keepalive 32;
}

# Then use upstream in location
location / {
    proxy_pass http://odoo_backend;  # Instead of http://127.0.0.1:8069
    # ... rest stays the same
}
```

#### 4.4 Add Caching for Static Assets

Edit `/etc/nginx/conf.d/nginx.conf`:

```nginx
# Cache static files
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    proxy_pass http://odoo_backend;
    proxy_cache_valid 200 60m;
    add_header Cache-Control "public, max-age=3600";
    expires 1h;
}
```

---

## 8. Complete Optimized Configuration

### Recommended `/etc/nginx/conf.d/nginx.conf`

```nginx
# Rate limiting (add to http block in main nginx.conf)
# limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
# limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

# Upstream with keepalive
upstream odoo_backend {
    server 127.0.0.1:8069;
    keepalive 32;
}

upstream odoo_longpolling {
    server 127.0.0.1:8072;
    keepalive 32;
}

# HTTPS server
server {
    listen 443 ssl http2 default_server;
    server_name od.emoment.tech odoo.emoment.tech;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/emoment.tech.pem;
    ssl_certificate_key /etc/nginx/ssl/emoment.tech.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Upload size
    client_max_body_size 100M;
    client_body_timeout 300s;

    # Restrict database manager
    location /web/database/manager {
        allow 127.0.0.1;
        # allow YOUR_IP;  # Add your IP
        deny all;

        proxy_pass http://odoo_backend;
        include /etc/nginx/proxy_params;
    }

    # Rate limit login
    location /web/login {
        # limit_req zone=login burst=3 nodelay;

        proxy_pass http://odoo_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://odoo_backend;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # WebSocket proxying
    location /websocket {
        proxy_pass http://odoo_longpolling;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }

    # Main location
    location / {
        proxy_pass http://odoo_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}

# HTTP redirect
server {
    listen 80;
    server_name od.emoment.tech odoo.emoment.tech;
    return 301 https://$host$request_uri;
}
```

---

## 9. Implementation Checklist

### Immediate Actions (Today)

- [ ] Enable `proxy_mode = True` in Odoo config
- [ ] Restart Odoo container
- [ ] Disable TLS 1.0 and 1.1
- [ ] Add `server_tokens off` in main config
- [ ] Restrict `/web/database/manager` access
- [ ] Test configuration: `nginx -t`
- [ ] Reload Nginx: `systemctl reload nginx`

### Short Term (This Week)

- [ ] Add security headers
- [ ] Implement rate limiting
- [ ] Enable full gzip compression
- [ ] Add upload size limits
- [ ] Optimize upstream connections
- [ ] Add static asset caching
- [ ] Review and clean up old backup configs

### Long Term (This Month)

- [ ] Set up proper SSL certificate monitoring
- [ ] Implement access logging for auditing
- [ ] Add fail2ban for automated blocking
- [ ] Set up monitoring/alerting for Nginx
- [ ] Document disaster recovery procedures
- [ ] Review and update firewall rules

---

## 10. Testing Commands

After implementing changes:

```bash
# Test configuration
sudo nginx -t

# Reload without downtime
sudo systemctl reload nginx

# Test HTTPS
curl -I https://odoo.emoment.tech

# Test rate limiting (should fail after 5 attempts)
for i in {1..10}; do curl -I https://odoo.emoment.tech/web/login; done

# Check headers
curl -I https://odoo.emoment.tech | grep -i "strict-transport\|x-frame\|x-content"

# Test SSL grade
ssl-test odoo.emoment.tech  # or use ssllabs.com
```

---

## 11. Monitoring Recommendations

### Log Files to Monitor

```bash
# Nginx access log
tail -f /var/log/nginx/access.log

# Nginx error log
tail -f /var/log/nginx/error.log

# Odoo logs
docker logs -f odoo-odoo-1
```

### Metrics to Track

1. **Response times** - Should be < 500ms for most requests
2. **Error rates** - Should be < 1%
3. **SSL handshake failures** - Should be minimal
4. **Rate limit triggers** - Monitor for DDoS attempts
5. **Upstream connection errors** - Check Odoo health

---

## 12. Security Scan Results

### Current Exposure (from logs)

Recent attack attempts detected:
- PHP injection attempts (line 1-2)
- Docker API probes (line 3)
- Router exploit attempts (line 5)
- Spring Boot actuator probes (line 6)

**Recommendation**: All blocked by current config, but add fail2ban

---

## Summary

**Current Grade**: C+
**Potential Grade**: A (after fixes)

### Critical Priorities

1. ✅ Proxy is working
2. ⚠️ Security needs improvement
3. ⚠️ Odoo proxy_mode must be enabled
4. ⚠️ TLS configuration needs hardening
5. ⚠️ Database manager needs restriction

**Estimated Time to Fix**: 2-4 hours for all priority 1 & 2 items

---

*Review completed: 2025-11-26*
*Next review recommended: 2025-12-26*
