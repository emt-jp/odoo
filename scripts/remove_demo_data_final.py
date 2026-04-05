#!/usr/bin/env python3
"""
Final: Delete remaining demo companies by executing SQL one statement at a time.
Each statement gets its own server action to avoid batch rollback issues.
"""

import xmlrpc.client
import sys
import time

URL = "https://odoo.emoment.tech"
DB = "odoo"
USER = "admin"
PWD = "admin"

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


def exec_sql(sql, desc=""):
    """Execute a single SQL statement via server action. Returns True on success."""
    safe_sql = sql.replace("\\", "\\\\").replace("'", "\\'")
    code = f"env.cr.execute('{safe_sql}')\nenv.cr.commit()"

    model_id = rpc('ir.model', 'search', [[('model', '=', 'res.partner')]])[0]
    action_id = rpc('ir.actions.server', 'create', [{
        'name': f'_sql_{int(time.time() * 1000) % 100000}',
        'model_id': model_id,
        'state': 'code',
        'code': code,
    }])

    success = True
    try:
        ctx = {'active_model': 'res.partner', 'active_id': 1, 'active_ids': [1]}
        rpc('ir.actions.server', 'run', [[action_id]], {'context': ctx})
        if desc:
            print(f"  OK: {desc}")
    except Exception as e:
        err = str(e)
        # Extract the actual SQL error
        if 'violates foreign key' in err:
            fk_start = err.find('on table')
            if fk_start > 0:
                fk_info = err[fk_start:fk_start+80]
                print(f"  FK: {desc} - {fk_info}")
            else:
                print(f"  FK: {desc} - {err[err.find('violates'):err.find('violates')+100]}")
        elif 'does not exist' in err and 'relation' in err:
            # Table doesn't exist, that's fine
            if desc:
                print(f"  SKIP (no table): {desc}")
        else:
            if desc:
                print(f"  FAIL: {desc} - {err[:200]}")
        success = False

    try:
        rpc('ir.actions.server', 'unlink', [[action_id]])
    except Exception:
        pass

    return success


def exec_sql_count(sql, desc=""):
    """Execute SQL and return affected row count."""
    safe_sql = sql.replace("\\", "\\\\").replace("'", "\\'")
    code = f"""
result = env.cr.execute('{safe_sql}')
env.cr.commit()
count = env.cr.rowcount
log('Cleanup: {desc} - %d rows affected' % count)
"""
    exec_sql(sql, desc)


def find_fk_refs(table_name):
    """Find all foreign key references to a table."""
    safe_table = table_name.replace("'", "\\'")
    code = f"""
env.cr.execute("SELECT tc.table_name, kcu.column_name, tc.constraint_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.constraint_type = 'FOREIGN KEY' AND kcu.constraint_name IN (SELECT constraint_name FROM information_schema.referential_constraints WHERE unique_constraint_name IN (SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = '{safe_table}' AND constraint_type IN ('PRIMARY KEY', 'UNIQUE')))")
refs = env.cr.fetchall()
# Store results in a global-ish place
raise Exception('FK_REFS:' + str(refs))
"""
    model_id = rpc('ir.model', 'search', [[('model', '=', 'res.partner')]])[0]
    action_id = rpc('ir.actions.server', 'create', [{
        'name': f'_fk_{int(time.time() * 1000) % 100000}',
        'model_id': model_id,
        'state': 'code',
        'code': code,
    }])

    refs = []
    try:
        ctx = {'active_model': 'res.partner', 'active_id': 1, 'active_ids': [1]}
        rpc('ir.actions.server', 'run', [[action_id]], {'context': ctx})
    except Exception as e:
        err = str(e)
        if 'FK_REFS:' in err:
            start = err.find('FK_REFS:') + 8
            end = err.find('\\n', start)
            if end < 0:
                end = err.find("'", start + 1)
            data = err[start:end]
            try:
                refs = eval(data)
            except Exception:
                pass

    try:
        rpc('ir.actions.server', 'unlink', [[action_id]])
    except Exception:
        pass

    return refs


def delete_company_cascade(company_id):
    """Delete a company by cascading through all FK references."""
    print(f"\n=== Deleting Company {company_id} ===")

    # Comprehensive list of tables with company_id FK, ordered by dependency
    # Each item is (table, column_name) - column defaults to 'company_id'
    tables = [
        # POS (deepest first)
        'pos_payment',
        'pos_order_line',
        'pos_order',
        'pos_session',
        'pos_payment_method',
        'pos_config',
        # Repair
        'repair_order',
        'repair_line',
        # Stock (deepest first)
        'stock_move_line',
        'stock_move',
        'stock_quant',
        'stock_lot',
        'stock_scrap',
        'stock_picking',
        'stock_warehouse_orderpoint',
        'stock_rule',
        'stock_picking_type',
        'stock_route_warehouse',
        'stock_route',
        'stock_warehouse',
        'stock_location',
        # Sale
        'sale_order_line',
        'sale_order',
        # Purchase
        'purchase_order_line',
        'purchase_order',
        # Accounting
        'account_partial_reconcile',
        'account_full_reconcile',
        'account_payment',
        'account_bank_statement_line',
        'account_bank_statement',
        'account_move_line',
        'account_move',
        'account_payment_method_line',
        'account_reconcile_model_line',
        'account_reconcile_model',
        'account_journal',
        'account_tax_repartition_line',
        'account_tax',
        'account_tax_group',
        'account_group',
        'account_fiscal_position',
        'account_account_tag',
        # HR
        'hr_leave',
        'hr_leave_allocation',
        'hr_attendance',
        'hr_expense',
        'hr_employee_skill',
        'hr_resume_line',
        'hr_employee',
        'hr_department',
        # CRM / Project
        'crm_lead',
        'project_update',
        'project_task',
        'project_project',
        # Planning
        'planning_slot',
        # Lunch
        'lunch_order',
        'lunch_cashmove',
        # Fleet
        'fleet_vehicle_log_services',
        'fleet_vehicle_log_fuel',
        'fleet_vehicle_log_contract',
        'fleet_vehicle_odometer',
        'fleet_vehicle_assignation_log',
        'fleet_vehicle',
        # Products
        'product_value',
        'product_supplierinfo',
        # Analytic
        'account_analytic_line',
        'account_analytic_account',
        'account_analytic_plan',
        # Gamification
        'gamification_badge_user',
        'gamification_goal',
        'gamification_challenge',
        # Mail
        'mail_alias',
        'mail_activity',
        # Misc infrastructure
        'ir_sequence',
        'ir_property',
        'ir_default',
        'digest_digest',
        'res_config_settings',
        'res_partner_bank',
        # Users relation
        'res_company_users_rel',
    ]

    for table in tables:
        col = 'cid' if table == 'res_company_users_rel' else 'company_id'
        sql = f"DELETE FROM {table} WHERE {col} = {company_id}"
        exec_sql(sql, f"{table}")

    # Now try the company itself
    print(f"\n  Attempting DELETE FROM res_company WHERE id = {company_id}")
    ok = exec_sql(f"DELETE FROM res_company WHERE id = {company_id}", f"res_company id={company_id}")
    if not ok:
        print(f"  Company {company_id} still has FK references. Searching...")
        # Use brute-force: find all tables that reference res_company
        refs = find_fk_refs('res_company')
        if refs:
            print(f"  Found {len(refs)} FK references:")
            for ref in refs:
                table, col, constraint = ref
                print(f"    {table}.{col} ({constraint})")
                sql = f"DELETE FROM {table} WHERE {col} = {company_id}"
                exec_sql(sql, f"  cascade {table}")

            # Retry
            ok = exec_sql(f"DELETE FROM res_company WHERE id = {company_id}", f"RETRY res_company id={company_id}")

    return ok


def main():
    connect()

    # Check what companies still exist
    companies = search_read('res.company', [], ['name'])
    remaining = [c for c in companies if c['id'] not in [4, 6]]

    if not remaining:
        print("All demo companies already deleted!")
        return

    print(f"\nRemaining demo companies: {[(c['id'], c['name']) for c in remaining]}")

    for company in remaining:
        delete_company_cascade(company['id'])

    # Fix admin
    print("\n=== Fixing admin user ===")
    exec_sql(f"DELETE FROM res_company_users_rel WHERE user_id = {uid} AND cid NOT IN (4, 6)", "clean admin companies")
    exec_sql(f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 4) ON CONFLICT DO NOTHING", "ensure admin co 4")
    exec_sql(f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 6) ON CONFLICT DO NOTHING", "ensure admin co 6")
    exec_sql(f"UPDATE res_users SET company_id = 4 WHERE id = {uid}", "set admin default co")

    # Verification
    print("\n\n=== FINAL VERIFICATION ===")

    companies = search_read('res.company', [], ['name'])
    print(f"\nCompanies ({len(companies)}):")
    for c in companies:
        status = "OK" if c['id'] in [4, 6] else "REMAINING"
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

    remaining_cos = [c for c in companies if c['id'] not in [4, 6]]
    if remaining_cos:
        print(f"\nWARNING: {len(remaining_cos)} demo companies could not be deleted")
    else:
        print("\nSUCCESS: All demo companies deleted!")


if __name__ == '__main__':
    main()
