# Apply Nginx Configuration Now

## Quick Start

Run this single command:

```bash
cd ~/ws/odoo && sudo ./apply_odoo_nginx.sh
```

That's it! The script will:
1. ✓ Backup your current configuration
2. ✓ Apply the new configuration (od.emoment.tech → odoo.emoment.tech)
3. ✓ Use existing emoment.tech SSL certificate (covers all subdomains)
4. ✓ Test the configuration
5. ✓ Reload nginx
6. ✓ Verify everything works

## What Changed

- **Domain**: `od.emoment.tech` → `odoo.emoment.tech`
- **SSL**: Using existing `/etc/nginx/ssl/emoment.tech.pem` (wildcard certificate)
- **Backend**: Still proxying to Odoo on ports 8069 and 8072

## After Applying

1. **Update DNS** (if not already done):
   - Add A record: `odoo.emoment.tech` → Your server IP
   - Enable Cloudflare proxy (orange cloud)

2. **Test it**:
   ```bash
   curl -I https://odoo.emoment.tech
   ```

3. **Check logs if needed**:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   sudo tail -f /var/log/nginx/error.log
   ```

## Rollback (if needed)

The script creates automatic backups. To rollback:

```bash
# List backups
ls -lt /etc/nginx/conf.d/nginx.conf.backup.*

# Restore a backup
sudo cp /etc/nginx/conf.d/nginx.conf.backup.YYYYMMDD_HHMMSS /etc/nginx/conf.d/nginx.conf
sudo systemctl reload nginx
```

## Files Created

- `nginx_odoo_emoment_tech.conf` - New configuration
- `apply_odoo_nginx.sh` - Application script (run with sudo)
- `validate_config.sh` - Validation script
- `APPLY_NOW.md` - This quick start guide
