# SSH Database Migration Guide

## Quick Start

### Option 1: Simple Script (Recommended)

```bash
# Run the simplified script
./ssh_export_import_simple.sh
```

The script will:
1. Prompt for SSH credentials
2. Auto-detect Odoo installation
3. Create backup on remote server
4. Download backup
5. Restore to Docker

### Option 2: Full Script (More Options)

```bash
# Run the full-featured script
./ssh_export_import.sh
```

---

## Prerequisites

### 1. SSH Access
You need SSH access to `od.emoment.tech`. Either:
- **SSH Key** (recommended): Place your private key in a secure location
- **Password**: Script will prompt for password

### 2. SSH Key Setup (Recommended)

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy public key to remote server
ssh-copy-id -i ~/.ssh/id_rsa.pub user@od.emoment.tech

# Test connection
ssh user@od.emoment.tech "echo 'Connected'"
```

### 3. Required Information

Before running, you'll need:
- SSH username
- SSH key path (or use password)
- Database name (usually "odoo")
- Database user (usually "odoo")
- Database password (if not in config file)

---

## Step-by-Step Process

### Step 1: Update Script Configuration

Edit `ssh_export_import_simple.sh` and update if needed:
```bash
REMOTE_HOST="od.emoment.tech"
REMOTE_USER=""  # Your SSH username
REMOTE_SSH_KEY=""  # Path to SSH key (optional)
REMOTE_DB="odoo"  # Database name
REMOTE_DB_USER="odoo"  # Database user
```

### Step 2: Run the Script

```bash
./ssh_export_import_simple.sh
```

### Step 3: Follow Prompts

The script will:
1. Ask for SSH username (if not set)
2. Ask for SSH key path (or use password)
3. Auto-detect Odoo installation
4. Read database configuration
5. Ask for database password (if needed)
6. Create backup on remote
7. Download backup
8. Restore to Docker

### Step 4: Verify

```bash
# Check Odoo logs
docker-compose logs odoo --tail=50

# Access Odoo
# URL: http://localhost:8069
# Use your remote database credentials
```

---

## Manual Steps (If Script Fails)

### 1. SSH to Remote Server

```bash
ssh user@od.emoment.tech
```

### 2. Find Odoo Installation

```bash
# Find odoo-bin
find /opt /home /var -name "odoo-bin" 2>/dev/null

# Find config file
find /opt /home /var -name "odoo.conf" 2>/dev/null
```

### 3. Create Backup

```bash
# Method 1: Using Odoo CLI
cd /path/to/odoo
python3 odoo-bin -c odoo.conf -d odoo --backup=/tmp/backup.dump --stop-after-init

# Method 2: Using pg_dump
pg_dump -U odoo -d odoo -F c -f /tmp/backup.dump
```

### 4. Download Backup

```bash
# From your local machine
scp user@od.emoment.tech:/tmp/backup.dump ./var/backups/
```

### 5. Restore to Docker

```bash
# Stop Odoo
docker-compose stop odoo

# Recreate database
docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;"
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;"

# Restore
cat var/backups/backup.dump | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl

# Start Odoo
docker-compose start odoo
```

---

## Troubleshooting

### SSH Connection Issues

**Problem**: "Permission denied (publickey)"
```bash
# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa

# Test connection
ssh -v user@od.emoment.tech
```

**Problem**: "Host key verification failed"
```bash
# Remove old host key
ssh-keygen -R od.emoment.tech

# Or add to known_hosts
ssh-keyscan od.emoment.tech >> ~/.ssh/known_hosts
```

### Database Backup Issues

**Problem**: "pg_dump: permission denied"
```bash
# Check database user permissions
# May need to run as postgres user or use Odoo CLI backup
```

**Problem**: "Odoo CLI backup fails"
```bash
# Use pg_dump directly instead
# The script will automatically fall back to pg_dump
```

### Restore Issues

**Problem**: "pg_restore: errors ignored"
```bash
# Some errors are normal (owner/permission issues)
# Check if data was restored:
docker-compose exec -T db psql -U odoo -d odoo -c "SELECT COUNT(*) FROM res_users;"
```

**Problem**: "Module errors after restore"
```bash
# Upgrade modules
python3 upgrade_module.py

# Or via Odoo UI: Apps > Upgrade
```

---

## Security Notes

⚠️ **Important Security Considerations**:

1. **SSH Keys**: Use SSH keys instead of passwords
2. **Key Permissions**: Set correct permissions: `chmod 600 ~/.ssh/id_rsa`
3. **Backup Files**: Backup files contain sensitive data
4. **Credentials**: Never commit credentials to git
5. **Cleanup**: Script automatically cleans up remote backup files

---

## Alternative: Using Odoo Web Backup

If SSH is not available, use Odoo's web interface:

1. Go to: `https://od.emoment.tech/web/database/manager`
2. Click "Backup" for your database
3. Download the `.dump` file
4. Use `backup_restore_database.sh` script (option 2)

---

## Post-Migration Steps

1. **Update Modules**:
   ```bash
   python3 upgrade_module.py
   ```

2. **Verify Data**:
   - Check record counts
   - Verify relationships
   - Test key functionality

3. **Update Configuration**:
   - Update email settings
   - Update file paths if needed
   - Configure local services

4. **Test Functionality**:
   - Create test records
   - Verify workflows
   - Check integrations

---

## Script Features

### Auto-Detection
- ✅ Finds Odoo installation automatically
- ✅ Reads database configuration from config file
- ✅ Detects backup format

### Error Handling
- ✅ Tests SSH connection first
- ✅ Falls back to alternative methods
- ✅ Provides clear error messages

### Cleanup
- ✅ Removes remote backup files after download
- ✅ Saves local backup for reference

---

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Review script output for error messages
3. Check Odoo logs: `docker-compose logs odoo`
4. Verify SSH access manually
5. Test database connection on remote server

