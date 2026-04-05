#!/usr/bin/env python3
"""
Phase 4: Use Odoo's ir.actions.server to execute raw SQL for stubborn records.
Creates a server action with Python code that uses env.cr.execute().
"""

import xmlrpc.client
import sys
import time

URL = "https://odoo.emoment.tech"
DB = "odoo"
USER = "admin"
PWD = "admin"

DEMO_COMPANIES = [1, 2, 3, 5]
KEEP_COMPANIES = [4, 6]
ALL_COMPANIES = [1, 2, 3, 4, 5, 6]
KEEP_EMPLOYEES = [22, 42, 43]

uid = None
models = None


def rpc(model, method, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    return models.execute_kw(DB, uid, PWD, model, method, args, kwargs)


def search(model, domain):
    try:
        return rpc(model, 'search', [domain])
    except Exception:
        return []


def search_read(model, domain, fields):
    return rpc(model, 'search_read', [domain], {'fields': fields})


def unlink(model, ids):
    if not ids:
        return
    try:
        rpc(model, 'unlink', [ids])
    except Exception as e:
        print(f"    unlink {model} failed: {str(e)[:150]}")


def write(model, ids, vals):
    if not ids:
        return
    rpc(model, 'write', [ids, vals])


def connect():
    global uid, models
    print(f"Connecting to {URL}...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PWD, {})
    if not uid:
        print("ERROR: Authentication failed!")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    print(f"Connected as UID={uid}")


def execute_sql(sql_statements, description="SQL batch"):
    """
    Execute raw SQL by creating a temporary server action.
    sql_statements: list of SQL strings to execute.
    """
    # Build Python code for the server action
    code_lines = ["# Auto-generated cleanup SQL"]
    for sql in sql_statements:
        # Escape single quotes in SQL for Python string
        safe_sql = sql.replace("'", "\\'")
        code_lines.append(f"env.cr.execute('{safe_sql}')")
    code_lines.append("env.cr.commit()")

    code = "\n".join(code_lines)

    print(f"\n  Executing: {description}")
    print(f"  ({len(sql_statements)} SQL statements)")

    # Create the server action
    action_id = rpc('ir.actions.server', 'create', [{
        'name': f'_cleanup_{int(time.time())}',
        'model_id': rpc('ir.model', 'search', [[('model', '=', 'res.partner')]])[0],
        'state': 'code',
        'code': code,
    }])

    # Execute it
    try:
        ctx = {'active_model': 'res.partner', 'active_id': 1, 'active_ids': [1]}
        rpc('ir.actions.server', 'run', [[action_id]], {'context': ctx})
        print(f"  OK: {description}")
    except Exception as e:
        err = str(e)
        if len(err) > 300:
            err = err[:300]
        print(f"  FAIL: {err}")

    # Clean up the server action
    try:
        rpc('ir.actions.server', 'unlink', [[action_id]])
    except Exception:
        pass

    return action_id


def execute_sql_single(sql, description=""):
    """Execute a single SQL statement."""
    return execute_sql([sql], description or sql[:80])


def main():
    connect()

    # Ensure admin has all company access
    print("\n--- Ensuring admin access ---")
    write('res.users', [uid], {
        'company_ids': [(6, 0, ALL_COMPANIES)],
        'company_id': 4
    })

    # ================================================================
    # STEP 1: POS data (the biggest blocker)
    # ================================================================
    print("\n=== STEP 1: POS Data ===")

    execute_sql([
        "DELETE FROM pos_payment WHERE pos_order_id IN (SELECT id FROM pos_order WHERE company_id IN (1,2,3,5))",
        "DELETE FROM pos_order_line WHERE order_id IN (SELECT id FROM pos_order WHERE company_id IN (1,2,3,5))",
        "DELETE FROM pos_order WHERE company_id IN (1,2,3,5)",
        "DELETE FROM pos_session WHERE company_id IN (1,2,3,5)",
        "DELETE FROM pos_payment_method WHERE company_id IN (1,2,3,5)",
        "DELETE FROM pos_config WHERE company_id IN (1,2,3,5)",
    ], "Delete POS data")

    # ================================================================
    # STEP 2: Leave allocations (blocks employees)
    # ================================================================
    print("\n=== STEP 2: Leave Allocations ===")

    execute_sql([
        "DELETE FROM hr_leave WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        "DELETE FROM hr_leave_allocation WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
    ], "Delete leave data")

    # ================================================================
    # STEP 3: Expenses (blocks employees)
    # ================================================================
    print("\n=== STEP 3: Expenses ===")

    execute_sql([
        "DELETE FROM hr_expense WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
    ], "Delete expenses")

    # ================================================================
    # STEP 4: Remaining employees in demo companies
    # ================================================================
    print("\n=== STEP 4: Demo Employees ===")

    # First check for any other FK references to employees
    execute_sql([
        # Planning slots
        "DELETE FROM planning_slot WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # Skill lines
        "DELETE FROM hr_employee_skill WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # Resume lines
        "DELETE FROM hr_resume_line WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # Gamification badge user
        "DELETE FROM gamification_badge_user WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # Delete employees
        "DELETE FROM hr_employee WHERE company_id IN (1,2,3,5)",
    ], "Delete demo employees")

    # ================================================================
    # STEP 5: Stock data
    # ================================================================
    print("\n=== STEP 5: Stock Data ===")

    execute_sql([
        # Stock move lines
        "DELETE FROM stock_move_line WHERE company_id IN (1,2,3,5)",
        # Stock moves
        "DELETE FROM stock_move WHERE company_id IN (1,2,3,5)",
        # Stock quants
        "DELETE FROM stock_quant WHERE company_id IN (1,2,3,5)",
        # Stock lots
        "DELETE FROM stock_lot WHERE company_id IN (1,2,3,5)",
        # Scrap
        "DELETE FROM stock_scrap WHERE company_id IN (1,2,3,5)",
        # Pickings
        "DELETE FROM stock_picking WHERE company_id IN (1,2,3,5)",
        # Orderpoints
        "DELETE FROM stock_warehouse_orderpoint WHERE company_id IN (1,2,3,5)",
        # Stock rules
        "DELETE FROM stock_rule WHERE company_id IN (1,2,3,5)",
        # Picking types
        "DELETE FROM stock_picking_type WHERE company_id IN (1,2,3,5)",
        # Routes - need to clear M2M first
        "DELETE FROM stock_route_warehouse WHERE route_id IN (SELECT id FROM stock_route WHERE company_id IN (1,2,3,5))",
        "DELETE FROM stock_route WHERE company_id IN (1,2,3,5)",
        # Warehouses
        "DELETE FROM stock_warehouse WHERE company_id IN (1,2,3,5)",
        # Locations (children first, use subquery)
        "DELETE FROM stock_location WHERE company_id IN (1,2,3,5) AND id NOT IN (SELECT COALESCE(location_id, 0) FROM stock_location WHERE company_id NOT IN (1,2,3,5))",
        "DELETE FROM stock_location WHERE company_id IN (1,2,3,5)",
    ], "Delete stock data")

    # ================================================================
    # STEP 6: Remaining accounting
    # ================================================================
    print("\n=== STEP 6: Accounting ===")

    execute_sql([
        # Move lines
        "DELETE FROM account_move_line WHERE company_id IN (1,2,3,5)",
        # Moves
        "DELETE FROM account_move WHERE company_id IN (1,2,3,5)",
        # Payment method lines
        "DELETE FROM account_payment_method_line WHERE company_id IN (1,2,3,5)",
        # Reconcile model lines
        "DELETE FROM account_reconcile_model_line WHERE model_id IN (SELECT id FROM account_reconcile_model WHERE company_id IN (1,2,3,5))",
        # Reconcile models
        "DELETE FROM account_reconcile_model WHERE company_id IN (1,2,3,5)",
        # Journals
        "DELETE FROM account_journal WHERE company_id IN (1,2,3,5)",
        # Taxes - clear M2M
        "DELETE FROM account_tax_repartition_line WHERE tax_id IN (SELECT id FROM account_tax WHERE company_id IN (1,2,3,5))",
        # Taxes
        "DELETE FROM account_tax WHERE company_id IN (1,2,3,5)",
        # Tax groups
        "DELETE FROM account_tax_group WHERE company_id IN (1,2,3,5)",
        # Account groups
        "DELETE FROM account_group WHERE company_id IN (1,2,3,5)",
        # Fiscal positions
        "DELETE FROM account_fiscal_position WHERE company_id IN (1,2,3,5)",
    ], "Delete accounting data")

    # ================================================================
    # STEP 7: Sequences, properties, misc
    # ================================================================
    print("\n=== STEP 7: Misc Data ===")

    execute_sql([
        # Sequences
        "DELETE FROM ir_sequence WHERE company_id IN (1,2,3,5)",
        # Properties
        "DELETE FROM ir_property WHERE company_id IN (1,2,3,5)",
        # Defaults
        "DELETE FROM ir_default WHERE company_id IN (1,2,3,5)",
        # Digest
        "DELETE FROM digest_digest WHERE company_id IN (1,2,3,5)",
        # Config settings
        "DELETE FROM res_config_settings WHERE company_id IN (1,2,3,5)",
        # Mail aliases with company
        "DELETE FROM mail_alias WHERE company_id IN (1,2,3,5)",
        # Bank accounts
        "DELETE FROM res_partner_bank WHERE company_id IN (1,2,3,5)",
        # Product values
        "DELETE FROM product_value WHERE company_id IN (1,2,3,5)",
        # Product supplierinfo
        "DELETE FROM product_supplierinfo WHERE company_id IN (1,2,3,5)",
    ], "Delete misc data")

    # ================================================================
    # STEP 8: Demo users
    # ================================================================
    print("\n=== STEP 8: Demo Users ===")

    execute_sql([
        # Mail messages by demo users
        "UPDATE mail_message SET author_id = 2 WHERE author_id IN (SELECT partner_id FROM res_users WHERE id IN (5, 6, 11))",
        # Project updates by demo users
        "DELETE FROM project_update WHERE user_id IN (5, 6, 11)",
        # Mail activities
        "DELETE FROM mail_activity WHERE user_id IN (5, 6, 11)",
        # Remove from groups M2M
        "DELETE FROM res_groups_users_rel WHERE uid IN (5, 6, 11)",
        # Remove company M2M
        "DELETE FROM res_company_users_rel WHERE user_id IN (5, 6, 11)",
        # Delete users
        "DELETE FROM res_users WHERE id IN (5, 6, 11)",
    ], "Delete demo users")

    # ================================================================
    # STEP 9: Delete companies
    # ================================================================
    print("\n=== STEP 9: Delete Companies ===")

    # First, remove admin from demo companies
    execute_sql([
        "DELETE FROM res_company_users_rel WHERE cid IN (1,2,3,5)",
    ], "Remove company user relations")

    # Delete each company one by one with its remaining dependencies
    for company_id in DEMO_COMPANIES:
        print(f"\n  --- Company {company_id} ---")
        execute_sql([
            # Catch-all: any remaining FK references
            f"DELETE FROM account_analytic_line WHERE company_id = {company_id}",
            f"DELETE FROM account_analytic_account WHERE company_id = {company_id}",
            f"DELETE FROM account_analytic_plan WHERE company_id = {company_id}",
            # Company itself
            f"DELETE FROM res_company WHERE id = {company_id}",
        ], f"Delete company {company_id}")

    # ================================================================
    # STEP 10: Fix admin user
    # ================================================================
    print("\n=== STEP 10: Fix Admin User ===")

    execute_sql([
        f"UPDATE res_users SET company_id = 4 WHERE id = {uid}",
        f"DELETE FROM res_company_users_rel WHERE user_id = {uid} AND cid NOT IN (4, 6)",
        f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 4) ON CONFLICT DO NOTHING",
        f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 6) ON CONFLICT DO NOTHING",
    ], "Fix admin companies")

    # ================================================================
    # VERIFICATION
    # ================================================================
    print("\n\n=== VERIFICATION ===")

    companies = search_read('res.company', [], ['name'])
    print(f"\nCompanies ({len(companies)}):")
    for c in companies:
        status = "OK" if c['id'] in KEEP_COMPANIES else "REMAINING"
        print(f"  ID={c['id']}: {c['name']} [{status}]")

    users = search_read('res.users', [], ['login', 'name'])
    print(f"\nUsers ({len(users)}):")
    for u in users:
        print(f"  ID={u['id']}: {u['name']} ({u['login']})")

    employees = search_read('hr.employee', [], ['name', 'company_id'])
    print(f"\nEmployees ({len(employees)}):")
    for e in employees:
        cn = e['company_id'][1] if e['company_id'] else 'None'
        print(f"  ID={e['id']}: {e['name']} ({cn})")

    depts = search_read('hr.department', [], ['name', 'company_id'])
    print(f"\nDepartments ({len(depts)}):")
    for d in depts:
        cn = d['company_id'][1] if d['company_id'] else 'None'
        print(f"  ID={d['id']}: {d['name']} ({cn})")

    admin = search_read('res.users', [('id', '=', uid)], ['company_id', 'company_ids'])
    if admin:
        print(f"\nAdmin default: {admin[0]['company_id']}")
        print(f"Admin companies: {admin[0]['company_ids']}")

    print("\n=== Done! ===")


if __name__ == '__main__':
    main()
