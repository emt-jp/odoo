# Quick Fix for odoo.emoment.tech

## Problem
- `od.emoment.tech` works ✓
- `odoo.emoment.tech` returns 404 ✗

## Root Cause
The nginx configuration only has `odoo.emoment.tech` in the server_name, but `od.emoment.tech` is working through Cloudflare (possibly cached or handled elsewhere).

## Solution: Support Both Domains

Run this command to make BOTH domains work:

```bash
cd ~/ws/odoo && sudo ./fix_both_domains.sh
```

This will:
1. Backup current config
2. Add both `od.emoment.tech` and `odoo.emoment.tech` to server_name
3. Test configuration
4. Reload nginx
5. Verify both domains work

## Alternative: Full Diagnostic

If the quick fix doesn't work, run a full diagnostic:

```bash
cd ~/ws/odoo && sudo ./diagnose_nginx.sh
```

This will show:
- All nginx processes
- All config files
- Which ports are listening
- Test results for both domains

## After Fix

Test both domains:
```bash
curl -I https://od.emoment.tech/web
curl -I https://odoo.emoment.tech/web
```

Both should return HTTP 303 (redirect to login page).

---

**Run the fix now:**
```bash
sudo ./fix_both_domains.sh
```
