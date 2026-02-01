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
max_cron_threads = 1

; Security
list_db = True
EOF

echo "Starting Odoo with config:"
cat /etc/odoo/odoo.conf | grep -v password

# Start Odoo
exec python3 /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf "$@"
