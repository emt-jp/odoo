# Download Nginx Config and SSL Certificates

## Quick Start

Run the automated script:
```bash
./download_nginx_ssl_auto.sh
```

You will be prompted for your SSH password for `as@103.101.59.102`.

## What the Script Does

1. **Finds Nginx Configuration**
   - Searches common locations: `/etc/nginx`, `/usr/local/nginx/conf`, etc.
   - Downloads `nginx.conf` and all config files
   - Downloads `sites-available/` and `conf.d/` directories

2. **Finds SSL Certificates**
   - Searches common locations: `/etc/letsencrypt/live`, `/etc/ssl/certs`, etc.
   - Downloads all certificate files
   - For Let's Encrypt, downloads by domain directory

3. **Saves Files**
   - Nginx config → `./ops/nginx/`
   - SSL certificates → `./ops/ssl/`

## Manual Download (If Script Fails)

### 1. Find Nginx Config Location
```bash
ssh as@103.101.59.102 "ls -la /etc/nginx/"
```

### 2. Download Nginx Config
```bash
# Main config
scp as@103.101.59.102:/etc/nginx/nginx.conf ./ops/nginx/

# Sites available
scp -r as@103.101.59.102:/etc/nginx/sites-available/* ./ops/nginx/sites-available/

# Conf.d
scp -r as@103.101.59.102:/etc/nginx/conf.d/* ./ops/nginx/conf.d/
```

### 3. Find SSL Certificates
```bash
ssh as@103.101.59.102 "ls -la /etc/letsencrypt/live/"
# or
ssh as@103.101.59.102 "ls -la /etc/ssl/certs/"
```

### 4. Download SSL Certificates
```bash
# Let's Encrypt (by domain)
scp -r as@103.101.59.102:/etc/letsencrypt/live/your-domain.com/* ./ops/ssl/your-domain.com/

# Or all domains
scp -r as@103.101.59.102:/etc/letsencrypt/live/* ./ops/ssl/
```

## After Download

1. **Review Nginx Config**
   - Check paths in config files
   - Update proxy_pass if needed
   - Verify SSL certificate paths

2. **Update for Local Use**
   - Update server_name if using different hostname
   - Update SSL certificate paths
   - Update upstream/proxy_pass to point to local Odoo (localhost:8069)

3. **Copy SSL Certificates**
   - If using nginx in Docker, mount certificates as volumes
   - If using host nginx, copy to `/etc/nginx/ssl/` or similar

4. **Test Configuration**
   ```bash
   nginx -t -c /path/to/nginx.conf
   ```

## Common Nginx Config Locations

- `/etc/nginx/` - Standard location
- `/usr/local/nginx/conf/` - Custom installation
- `~/nginx/` - User installation

## Common SSL Certificate Locations

- `/etc/letsencrypt/live/` - Let's Encrypt certificates
- `/etc/ssl/certs/` - System certificates
- `/etc/nginx/ssl/` - Nginx-specific certificates
- `~/ssl/` or `~/certs/` - User certificates

## Next Steps

After downloading:
1. Review the nginx configuration
2. Update paths for your local setup
3. Configure nginx to proxy to your Docker Odoo instance
4. Test the configuration
5. Restart nginx

