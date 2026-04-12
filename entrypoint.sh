#!/bin/bash
set -e

# Generate odoo.conf from environment variables
cat > /etc/odoo/odoo.conf << EOF
[options]
; Database settings
db_host = ${DB_HOST:-localhost}
db_port = ${DB_PORT:-5432}
db_user = ${DB_USER:-odoo}
db_password = ${DB_PASSWORD:-odoo}
db_name = ${DB_NAME:-odoo}

; Addons path
addons_path = /opt/odoo/addons,/opt/odoo/odoo/addons

; Admin password
admin_passwd = ${ADMIN_PASSWD:-admin}

; Server settings
http_port = 8069
proxy_mode = True
workers = 0

; Logging - use stdout for Cloud Run
log_level = info
logfile = False

; Performance
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_time_cpu = 600
limit_time_real = 1200

; Data directory
data_dir = /var/lib/odoo

; Session settings
max_cron_threads = ${MAX_CRON_THREADS:-1}

; Security
list_db = True
EOF

echo "Starting Odoo with config:"
cat /etc/odoo/odoo.conf | grep -v password

# Run module upgrade for car_rental_fleet before serving HTTP. Idempotent —
# Odoo's -u is a fast no-op when ir_module_module.latest_version already
# matches the manifest. When the manifest version was bumped (schema change),
# this is the only place the migration can run safely on Cloud Run, since
# Cloud Run can't exec into the running container. set -e + --stop-after-init
# means a failed migration aborts the container, Cloud Run keeps the old
# revision live, no broken state ever serves traffic.
UPGRADE_MODULE="${UPGRADE_MODULE:-car_rental_fleet}"
if [ -n "$UPGRADE_MODULE" ]; then
    echo "Running module upgrade for: $UPGRADE_MODULE"
    python3 /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf -u "$UPGRADE_MODULE" --stop-after-init
    echo "Module upgrade complete."
fi

# Start Odoo HTTP server
exec python3 /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf "$@"
