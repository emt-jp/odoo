#!/bin/bash

echo "======================================================================="
echo "🚀 Complete Odoo Module Installation & Testing"
echo "======================================================================="

# Function to install module via CLI
install_module_cli() {
    local module=$1
    echo ""
    echo "📦 Installing $module via Odoo CLI..."

    docker exec odoo-odoo-1 bash -c "
        python3 /opt/odoo/odoo-bin -d odoo -c /etc/odoo/odoo.conf \
            --stop-after-init \
            --without-demo=all \
            -i $module 2>&1 | grep -E 'Loading|loaded|Modules|ERROR|Error' | tail -20
    " || echo "  ⚠ Module $module installation had issues"
}

# Function to check module status
check_module() {
    local module=$1
    docker exec odoo-psql-1 psql -U odoo -d odoo -t -c \
        "SELECT state FROM ir_module_module WHERE name = '$module';" 2>/dev/null | xargs
}

# Restart Odoo to apply changes
restart_odoo() {
    echo ""
    echo "🔄 Restarting Odoo..."
    docker restart odoo-odoo-1
    sleep 10
    echo "✓ Odoo restarted"
}

# Install modules in order
MODULES=(
    "auth_signup"
    "portal"
    "utm"
    "resource"
    "account"
    "sale_management"
    "crm"
    "stock"
    "hr"
    "project"
    "fleet"
    "car_rental_fleet"
    "advanced_analytics"
    "advanced_crm"
    "advanced_inventory"
    "advanced_reports"
)

echo ""
echo "Phase 1: Installing core dependencies..."
echo "======================================================================="

for module in "${MODULES[@]}"; do
    current_state=$(check_module "$module")
    echo ""
    echo "Module: $module (current state: $current_state)"

    if [ "$current_state" != "installed" ]; then
        install_module_cli "$module"
    else
        echo "  ℹ Already installed"
    fi
done

# Restart Odoo
restart_odoo

echo ""
echo "======================================================================="
echo "Phase 2: Verifying installations..."
echo "======================================================================="

docker exec odoo-psql-1 psql -U odoo -d odoo -c \
    "SELECT name, state FROM ir_module_module WHERE name IN ('account', 'sale_management', 'crm', 'stock', 'hr', 'project', 'fleet', 'car_rental_fleet', 'advanced_analytics', 'advanced_crm', 'advanced_inventory', 'advanced_reports') ORDER BY name;"

echo ""
echo "======================================================================="
echo "✅ Installation Complete!"
echo "======================================================================="
