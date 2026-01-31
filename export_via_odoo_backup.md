# Export Data from od.emoment.tech to Docker Instance

## Method 1: Using Odoo's Built-in Backup Feature (Recommended)

### Step 1: Create Backup from Remote Instance

1. **Access Odoo Database Manager**
   - Go to: `https://od.emoment.tech/web/database/manager`
   - Login with your admin credentials

2. **Create Backup**
   - Click on your database name
   - Click "Backup" button
   - Enter master password (if set)
   - Download the backup file (`.dump` format)

3. **Save Backup File**
   - Save the downloaded file to: `/home/as/ws/odoo/var/backups/`
   - Note the filename for next step

### Step 2: Restore to Docker Instance

```bash
# Make script executable
chmod +x backup_restore_database.sh

# Run restore script
./backup_restore_database.sh
# Choose option 2 (Restore database to local Docker)
```

Or manually:

```bash
# Stop Odoo
docker-compose stop odoo

# Drop and recreate database
docker-compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;"
docker-compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo;"

# Restore backup (replace BACKUP_FILE.dump with your file)
cat var/backups/BACKUP_FILE.dump | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl

# Start Odoo
docker-compose start odoo
```

---

## Method 2: Using XML-RPC Export/Import (Selective Data)

### Step 1: Update Credentials

Edit `export_import_data.py` and update:
- `REMOTE_URL` - Your remote Odoo URL
- `REMOTE_DB` - Your database name
- `REMOTE_USERNAME` - Your username
- `REMOTE_PASSWORD` - Your password

### Step 2: Run Export/Import Script

```bash
# Make executable
chmod +x export_import_data.py

# Run script
python3 export_import_data.py
```

This will:
- Export data from remote models
- Import to local Docker instance
- Handle relationships and foreign keys

---

## Method 3: Direct PostgreSQL Dump (If Accessible)

### Step 1: Export from Remote

```bash
# If you have SSH access to remote server
pg_dump -h od.emoment.tech -U odoo -d odoo -F c -f var/backups/remote_backup.dump

# Or if using SSH tunnel
ssh user@od.emoment.tech "pg_dump -U odoo -d odoo -F c" > var/backups/remote_backup.dump
```

### Step 2: Restore to Docker

```bash
# Stop Odoo
docker-compose stop odoo

# Restore
cat var/backups/remote_backup.dump | docker-compose exec -T db pg_restore -U odoo -d odoo --no-owner --no-acl

# Start Odoo
docker-compose start odoo
```

---

## Method 4: Using Odoo's Export/Import Wizard (UI Method)

### Step 1: Export from Remote

1. Go to remote Odoo: `https://od.emoment.tech`
2. Navigate to any model (e.g., Fleet > Vehicles)
3. Click "Export" button
4. Select fields to export
5. Download CSV/Excel file

### Step 2: Import to Local

1. Go to local Odoo: `http://localhost:8069`
2. Navigate to same model
3. Click "Import" button
4. Upload the CSV/Excel file
5. Map fields and import

**Note**: This method works for individual models and requires manual work for each model.

---

## Recommended Approach

**For Full Database Migration**: Use Method 1 (Odoo Backup Feature)
- Easiest and most reliable
- Preserves all data, relationships, and settings
- Single file backup

**For Selective Data Migration**: Use Method 2 (XML-RPC Script)
- More control over what to migrate
- Can filter and transform data
- Good for specific models only

---

## After Restore

1. **Update Module** (if needed):
   ```bash
   python3 upgrade_module.py
   ```

2. **Check Logs**:
   ```bash
   docker-compose logs odoo --tail=50
   ```

3. **Access Odoo**:
   - URL: http://localhost:8069
   - Use your remote database credentials

4. **Verify Data**:
   - Check that all models have data
   - Verify relationships are intact
   - Test key functionality

---

## Troubleshooting

### Issue: Backup file not found
- Check file path and permissions
- Ensure backup was downloaded completely

### Issue: Restore fails
- Check database user permissions
- Ensure Odoo container is stopped
- Check disk space

### Issue: Module errors after restore
- Upgrade the module: `python3 upgrade_module.py`
- Check for missing dependencies
- Review Odoo logs

### Issue: Authentication fails
- Verify credentials in scripts
- Check if remote instance allows XML-RPC
- Verify database name is correct

---

## Security Notes

⚠️ **Important**:
- Never commit backup files to git
- Use secure methods for password transfer
- Consider using environment variables for credentials
- Backup files may contain sensitive data

