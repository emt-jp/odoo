# Fix Cloudflare 404 Error

## Issue Identified

✓ **Nginx:** Working correctly (reloaded successfully)
✓ **Odoo Backend:** Running and responding locally on port 8069
✓ **DNS:** Resolving to Cloudflare IPs (proxied)
✗ **Problem:** Cloudflare returning 404 - not reaching your origin server

## Your Server IP

**Public IPv4:** `46.250.252.111`
**Public IPv6:** `2400:d320:2282:9400::1`

## Solution: Update Cloudflare DNS Record

### Step 1: Verify/Update DNS A Record

Go to **Cloudflare Dashboard** → **DNS** → **Records**

Make sure the `odoo` A record is configured as:

```
Type: A
Name: odoo
IPv4 address: 46.250.252.111
Proxy status: Proxied (☁️ orange cloud)
TTL: Auto
```

### Step 2: Verify SSL/TLS Settings

Go to **Cloudflare Dashboard** → **SSL/TLS** → **Overview**

**IMPORTANT:** Set encryption mode to **Full (strict)**

- ✓ Full (strict) - Recommended (encrypts end-to-end with valid certificate)
- ✗ Flexible - Will NOT work (Cloudflare connects via HTTP to origin)
- ✗ Full - Might work but less secure

### Step 3: Check Firewall Rules (Optional)

If still not working, you may need to allow Cloudflare IPs:

```bash
# Check if firewall is blocking
sudo ufw status

# If UFW is active, allow Cloudflare IPs (optional)
# This allows Cloudflare to connect to your origin
```

## Testing After Fix

Once you update the DNS A record to point to `46.250.252.111`:

```bash
# Wait 1-2 minutes for propagation, then test:
curl -I https://odoo.emoment.tech/web

# Or open in browser:
https://odoo.emoment.tech/web
```

## Expected Result

After fixing, you should see:
- A redirect to `/web/login` (Odoo login page)
- HTTP 200 or 303 status (not 404)

## Current Test Results

### ✓ Local Backend Test (Working):
```bash
$ curl -I http://127.0.0.1:8069/odoo
HTTP/1.0 303 SEE OTHER
Location: /web/login?redirect=%2Fodoo%3F
```

### ✗ Public Test (Not Working):
```bash
$ curl -I https://odoo.emoment.tech/odoo
HTTP/2 404
```

This confirms the issue is with Cloudflare → Origin connection, not your nginx/Odoo setup.

## Quick Checklist

- [ ] DNS A record points to `46.250.252.111`
- [ ] SSL/TLS mode set to "Full (strict)"
- [ ] Orange cloud (proxy) is enabled
- [ ] Wait 1-2 minutes for changes to propagate
- [ ] Test: `curl -I https://odoo.emoment.tech/web`

---

**Once the DNS is correctly pointing to your server IP, everything will work!**
