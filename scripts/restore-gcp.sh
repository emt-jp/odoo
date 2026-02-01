#!/bin/bash
# Restore Odoo to GCP
# Run this from your local machine after downloading the backup

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-asia-northeast1}"
INSTANCE_NAME="${INSTANCE_NAME:-odoo-db}"
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_ID}-odoo-filestore}"

WORK_DIR="/tmp/odoo-restore-$(date +%Y%m%d-%H%M%S)"

echo "Extracting backup to $WORK_DIR..."
mkdir -p "$WORK_DIR"
tar -xzf "$BACKUP_FILE" -C "$WORK_DIR"

# Upload database dump to GCS
echo "Uploading database dump to GCS..."
gsutil cp "$WORK_DIR/odoo.dump" "gs://${BUCKET_NAME}/migration/odoo.dump"

# Import database to Cloud SQL
echo "Importing database to Cloud SQL..."
echo "Note: This requires the database dump to be in SQL format for gcloud sql import"
echo "For custom format dumps, use pg_restore via Cloud SQL Auth Proxy"

# Option 1: Using gcloud sql import (requires SQL format)
# gcloud sql import sql "$INSTANCE_NAME" "gs://${BUCKET_NAME}/migration/odoo.sql" \
#     --database=odoo \
#     --project="$PROJECT_ID"

# Option 2: Using pg_restore via Cloud SQL Auth Proxy (recommended)
echo ""
echo "To import using pg_restore:"
echo "1. Start Cloud SQL Auth Proxy:"
echo "   cloud-sql-proxy ${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
echo ""
echo "2. Run pg_restore:"
echo "   pg_restore -h localhost -p 5432 -U odoo -d odoo -v $WORK_DIR/odoo.dump"
echo ""

# Upload filestore to GCS
if [ -f "$WORK_DIR/filestore.tar.gz" ]; then
    echo "Uploading filestore to GCS..."
    FILESTORE_DIR="$WORK_DIR/filestore"
    mkdir -p "$FILESTORE_DIR"
    tar -xzf "$WORK_DIR/filestore.tar.gz" -C "$FILESTORE_DIR"
    gsutil -m cp -r "$FILESTORE_DIR/*" "gs://${BUCKET_NAME}/filestore/"
    echo "Filestore uploaded to gs://${BUCKET_NAME}/filestore/"
fi

# Copy addons
if [ -f "$WORK_DIR/addons.tar.gz" ]; then
    echo "Extracting custom addons..."
    ADDONS_DIR="../addons"
    mkdir -p "$ADDONS_DIR"
    tar -xzf "$WORK_DIR/addons.tar.gz" -C "$ADDONS_DIR"
    echo "Custom addons extracted to $ADDONS_DIR"
fi

echo ""
echo "Migration preparation complete!"
echo ""
echo "Next steps:"
echo "1. Review and commit custom addons to git"
echo "2. Import database using Cloud SQL Auth Proxy"
echo "3. Update Odoo configuration for GCS filestore"
echo "4. Build and deploy Docker image"
echo "5. Test the deployment"
