#!/bin/bash
# Fix PCP PostgreSQL monitoring configuration

echo "Backing up current PCP PostgreSQL config..."
cp /etc/pcp/postgresql/pmdapostgresql.conf /etc/pcp/postgresql/pmdapostgresql.conf.backup

echo "Updating PCP PostgreSQL configuration..."
cat > /etc/pcp/postgresql/pmdapostgresql.conf << 'EOF'
[authentication]
host=localhost
port=5432
dbname=odoo
user=odoo
password=odoo
osuser=pcp
EOF

echo "New configuration:"
cat /etc/pcp/postgresql/pmdapostgresql.conf

echo ""
echo "Restarting PCP daemon..."
systemctl restart pmcd

echo ""
echo "Checking PCP daemon status..."
systemctl status pmcd --no-pager -l

echo ""
echo "Done! Monitoring Docker logs for a few seconds..."
sleep 5

echo ""
echo "Recent PostgreSQL logs:"
cd /home/as/ws/odoo && docker compose logs psql --tail=20
