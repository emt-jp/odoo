#!/bin/bash
# Backup Odoo from Contabo VPS
# Run this on the Contabo VPS

set -e

BACKUP_DIR="/tmp/odoo-backup-$(date +%Y%m%d-%H%M%S)"
DB_NAME="odoo"
DB_USER="odoo"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL database
echo "Backing up PostgreSQL database..."
pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_DIR/odoo.dump"

# Backup filestore
echo "Backing up filestore..."
FILESTORE_PATH="/var/lib/odoo/.local/share/Odoo/filestore/$DB_NAME"
if [ -d "$FILESTORE_PATH" ]; then
    tar -czf "$BACKUP_DIR/filestore.tar.gz" -C "$FILESTORE_PATH" .
else
    echo "Warning: Filestore not found at $FILESTORE_PATH"
fi

# Backup custom addons
echo "Backing up custom addons..."
ADDONS_PATH="/opt/odoo/custom-addons"
if [ -d "$ADDONS_PATH" ]; then
    tar -czf "$BACKUP_DIR/addons.tar.gz" -C "$ADDONS_PATH" .
else
    echo "Warning: Custom addons not found at $ADDONS_PATH"
fi

# Backup configuration
echo "Backing up configuration..."
cp /etc/odoo/odoo.conf "$BACKUP_DIR/"

# Create final archive
echo "Creating final archive..."
tar -czf "/tmp/odoo-full-backup-$(date +%Y%m%d).tar.gz" -C "$BACKUP_DIR" .

echo "Backup complete: /tmp/odoo-full-backup-$(date +%Y%m%d).tar.gz"
echo ""
echo "To transfer to your local machine:"
echo "  scp user@contabo:/tmp/odoo-full-backup-*.tar.gz ."
