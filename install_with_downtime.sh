#!/bin/bash

echo "======================================================================="
echo "🚀 Odoo Module Installation (with service restart)"
echo "======================================================================="

# Stop Odoo
echo "🛑 Stopping Odoo service..."
docker stop odoo-odoo-1
sleep 3

# Install modules
MODULES="account,sale_management,crm,stock,hr,project,car_rental_fleet,advanced_analytics,advanced_crm,advanced_inventory,advanced_reports"

echo ""
echo "📦 Installing modules: $MODULES"
echo ""

docker run --rm \
    --network odoo_default \
    -v /home/as/ws/odoo/addons:/mnt/extra-addons \
    -v /home/as/ws/odoo/odoo:/opt/odoo/odoo \
    -v /home/as/ws/odoo/ops/config/odoo.conf:/etc/odoo/odoo.conf \
    odoo-odoo \
    python3 /opt/odoo/odoo-bin -d odoo -c /etc/odoo/odoo.conf \
        --stop-after-init \
        --without-demo=all \
        -i $MODULES 2>&1 | tee /home/as/ws/odoo/var/logs/module_install.log

echo ""
echo "✅ Module installation complete"
echo ""

# Start Odoo
echo "🚀 Starting Odoo service..."
docker start odoo-odoo-1
sleep 10

echo ""
echo "✓ Odoo service started"
echo ""

# Check installation status
echo "📊 Checking module status..."
docker exec odoo-psql-1 psql -U odoo -d odoo -c \
    "SELECT name, state FROM ir_module_module WHERE name IN ('account', 'sale_management', 'crm', 'stock', 'hr', 'project', 'fleet', 'car_rental_fleet', 'advanced_analytics', 'advanced_crm', 'advanced_inventory', 'advanced_reports') ORDER BY name;"

echo ""
echo "======================================================================="
echo "✅ Done!"
echo "======================================================================="
