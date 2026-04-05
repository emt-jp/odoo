#!/usr/bin/env python3
"""
Targeted cleanup: handle specific FK blockers preventing company deletion.
Key blockers:
1. pos_session → references pos_config (not company_id directly)
2. payment_provider → references company
3. res_company.internal_transit_location_id → self-referencing FK to stock_location
4. stock_warehouse.pbm_route_id etc. → circular FK with stock_route
5. Tables without company_id (use subqueries instead)
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
    """Execute a single SQL statement via server action."""
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
        if "does not exist" in err and ("relation" in err or "column" in err):
            if desc:
                print(f"  SKIP (not found): {desc}")
        elif "violates foreign key" in err:
            fk_part = err[err.find('violates'):err.find('violates')+120] if 'violates' in err else err[:200]
            print(f"  FK: {desc} - {fk_part}")
        else:
            print(f"  FAIL: {desc} - {err[:250]}")
        success = False

    try:
        rpc('ir.actions.server', 'unlink', [[action_id]])
    except Exception:
        pass

    return success


def exec_sql_multi(statements, desc="batch"):
    """Execute multiple SQL statements, each independently."""
    print(f"\n--- {desc} ---")
    for sql in statements:
        short_desc = sql[:80].replace("DELETE FROM ", "del ").replace(" WHERE ", " W ")
        exec_sql(sql, short_desc)


def main():
    connect()

    # ====================================================================
    # 1. POS sessions - they use config_id, not company_id
    # ====================================================================
    exec_sql_multi([
        # POS payments reference pos_order
        "DELETE FROM pos_payment WHERE pos_order_id IN (SELECT id FROM pos_order WHERE session_id IN (SELECT id FROM pos_session WHERE config_id IN (SELECT id FROM pos_config WHERE company_id IN (1,2,3,5))))",
        # POS order lines
        "DELETE FROM pos_order_line WHERE order_id IN (SELECT id FROM pos_order WHERE session_id IN (SELECT id FROM pos_session WHERE config_id IN (SELECT id FROM pos_config WHERE company_id IN (1,2,3,5))))",
        # POS orders
        "DELETE FROM pos_order WHERE session_id IN (SELECT id FROM pos_session WHERE config_id IN (SELECT id FROM pos_config WHERE company_id IN (1,2,3,5)))",
        # POS sessions themselves
        "DELETE FROM pos_session WHERE config_id IN (SELECT id FROM pos_config WHERE company_id IN (1,2,3,5))",
        # POS payment methods (may use journal FK instead of company)
        "DELETE FROM pos_payment_method WHERE journal_id IN (SELECT id FROM account_journal WHERE company_id IN (1,2,3,5))",
        "DELETE FROM pos_payment_method WHERE company_id IN (1,2,3,5)",
        # POS configs
        "DELETE FROM pos_config WHERE company_id IN (1,2,3,5)",
    ], "POS cleanup")

    # ====================================================================
    # 2. NULL out circular FKs in stock
    # ====================================================================
    exec_sql_multi([
        # Null out warehouse's route references (circular FK)
        "UPDATE stock_warehouse SET pbm_route_id = NULL, reception_route_id = NULL, delivery_route_id = NULL, crossdock_route_id = NULL, pbm_loc_id = NULL, lot_stock_id = NULL, wh_input_stock_loc_id = NULL, wh_output_stock_loc_id = NULL, wh_pack_stock_loc_id = NULL, wh_qc_stock_loc_id = NULL WHERE company_id IN (1,2,3,5)",
        # Null out company's internal transit location (circular FK)
        "UPDATE res_company SET internal_transit_location_id = NULL WHERE id IN (1,2,3,5)",
        # Now delete stock routes
        "DELETE FROM stock_route_warehouse WHERE route_id IN (SELECT id FROM stock_route WHERE company_id IN (1,2,3,5))",
        "DELETE FROM stock_route WHERE company_id IN (1,2,3,5)",
        # Delete warehouses
        "DELETE FROM stock_warehouse WHERE company_id IN (1,2,3,5)",
        # Delete picking types (need to null out location FKs)
        "UPDATE stock_picking_type SET default_location_src_id = NULL, default_location_dest_id = NULL WHERE company_id IN (1,2,3,5)",
        "DELETE FROM stock_picking_type WHERE company_id IN (1,2,3,5)",
        # Delete locations (children first via WITH RECURSIVE)
        "DELETE FROM stock_location WHERE company_id IN (1,2,3,5)",
    ], "Stock circular FK cleanup")

    # ====================================================================
    # 3. Account journals (blocked by POS config FK, now should be clear)
    # ====================================================================
    exec_sql_multi([
        "DELETE FROM account_payment_method_line WHERE journal_id IN (SELECT id FROM account_journal WHERE company_id IN (1,2,3,5))",
        "DELETE FROM account_journal WHERE company_id IN (1,2,3,5)",
    ], "Journals cleanup")

    # ====================================================================
    # 4. Payment providers and similar
    # ====================================================================
    exec_sql_multi([
        "DELETE FROM payment_token WHERE provider_id IN (SELECT id FROM payment_provider WHERE company_id IN (1,2,3,5))",
        "DELETE FROM payment_transaction WHERE provider_id IN (SELECT id FROM payment_provider WHERE company_id IN (1,2,3,5))",
        "DELETE FROM payment_provider WHERE company_id IN (1,2,3,5)",
    ], "Payment providers")

    # ====================================================================
    # 5. Remaining misc tables that might not have company_id directly
    # ====================================================================
    exec_sql_multi([
        # account_full_reconcile doesn't have company_id; it's linked through partial reconciles
        "DELETE FROM account_full_reconcile WHERE id NOT IN (SELECT DISTINCT full_reconcile_id FROM account_partial_reconcile WHERE full_reconcile_id IS NOT NULL)",
        # account_account_tag - might not have company_id, try country_id approach
        # Actually, in Odoo 19, account.account doesn't have company_id
        # Just try different column names
    ], "Misc cleanup")

    # ====================================================================
    # 6. Tables that might use different column names
    # ====================================================================
    exec_sql_multi([
        # hr_leave_allocation might not have company_id, use employee subquery
        "DELETE FROM hr_leave_allocation WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # Same for hr_attendance
        "DELETE FROM hr_attendance WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # hr_employee_skill
        "DELETE FROM hr_employee_skill WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # hr_resume_line
        "DELETE FROM hr_resume_line WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        # gamification
        "DELETE FROM gamification_badge_user WHERE employee_id IN (SELECT id FROM hr_employee WHERE company_id IN (1,2,3,5))",
        "DELETE FROM gamification_goal WHERE user_id IN (SELECT id FROM res_users WHERE company_id IN (1,2,3,5))",
        "DELETE FROM gamification_challenge WHERE company_id IN (1,2,3,5)",
        # project_update - might use company_id indirectly
        "DELETE FROM project_update WHERE project_id IN (SELECT id FROM project_project WHERE company_id IN (1,2,3,5))",
        # fleet odometer
        "DELETE FROM fleet_vehicle_odometer WHERE vehicle_id IN (SELECT id FROM fleet_vehicle WHERE company_id IN (1,2,3,5))",
        # fleet assignation
        "DELETE FROM fleet_vehicle_assignation_log WHERE vehicle_id IN (SELECT id FROM fleet_vehicle WHERE company_id IN (1,2,3,5))",
        # mail_alias
        "DELETE FROM mail_alias WHERE id IN (SELECT alias_id FROM pos_config WHERE company_id IN (1,2,3,5) AND alias_id IS NOT NULL)",
        # mail_activity
        "DELETE FROM mail_activity WHERE res_model_id IN (SELECT id FROM ir_model WHERE model IN ('res.company')) AND res_id IN (1,2,3,5)",
        # account_analytic_plan
        "DELETE FROM account_analytic_plan WHERE company_id IN (1,2,3,5)",
    ], "Indirect FK cleanup")

    # ====================================================================
    # 7. Broad sweep: find ALL remaining FK references to res_company
    # ====================================================================
    print("\n--- Broad sweep: query all FK refs to res_company ---")

    # Use server action to query information_schema and delete
    code = """
# Find all tables with FK to res_company
env.cr.execute(\"\"\"
    SELECT DISTINCT kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'res_company'
    AND ccu.column_name = 'id'
    ORDER BY kcu.table_name
\"\"\")
refs = env.cr.fetchall()

deleted_tables = []
for table_name, col_name in refs:
    if table_name == 'res_company':
        continue
    try:
        env.cr.execute(f"DELETE FROM {table_name} WHERE {col_name} IN (1,2,3,5)")
        env.cr.commit()
        if env.cr.rowcount > 0:
            deleted_tables.append(f"{table_name}.{col_name}:{env.cr.rowcount}")
    except Exception as e:
        env.cr.rollback()
        # Try NULLing instead
        try:
            env.cr.execute(f"UPDATE {table_name} SET {col_name} = NULL WHERE {col_name} IN (1,2,3,5)")
            env.cr.commit()
            if env.cr.rowcount > 0:
                deleted_tables.append(f"{table_name}.{col_name}:NULL:{env.cr.rowcount}")
        except Exception:
            env.cr.rollback()

# Report via exception (only way to get data back)
raise Exception('SWEEP_RESULT:' + '|'.join(deleted_tables) + ':END')
"""

    model_id = rpc('ir.model', 'search', [[('model', '=', 'res.partner')]])[0]
    action_id = rpc('ir.actions.server', 'create', [{
        'name': f'_sweep_{int(time.time() * 1000) % 100000}',
        'model_id': model_id,
        'state': 'code',
        'code': code,
    }])

    try:
        ctx = {'active_model': 'res.partner', 'active_id': 1, 'active_ids': [1]}
        rpc('ir.actions.server', 'run', [[action_id]], {'context': ctx})
    except Exception as e:
        err = str(e)
        if 'SWEEP_RESULT:' in err:
            start = err.find('SWEEP_RESULT:') + 13
            end = err.find(':END', start)
            results = err[start:end] if end > 0 else err[start:start+500]
            if results:
                print(f"  Sweep results: {results}")
            else:
                print("  Sweep: no records found to delete")
        else:
            print(f"  Sweep error: {err[:300]}")

    try:
        rpc('ir.actions.server', 'unlink', [[action_id]])
    except Exception:
        pass

    # ====================================================================
    # 8. Now attempt company deletion
    # ====================================================================
    print("\n--- Deleting companies ---")
    for cid in [5, 3, 2, 1]:
        exec_sql(f"DELETE FROM res_company WHERE id = {cid}", f"DELETE company {cid}")

    # ====================================================================
    # 9. Fix admin
    # ====================================================================
    print("\n--- Fix admin ---")
    exec_sql(f"DELETE FROM res_company_users_rel WHERE user_id = {uid} AND cid NOT IN (4, 6)", "clean admin")
    exec_sql(f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 4) ON CONFLICT DO NOTHING", "ensure co 4")
    exec_sql(f"INSERT INTO res_company_users_rel (user_id, cid) VALUES ({uid}, 6) ON CONFLICT DO NOTHING", "ensure co 6")
    exec_sql(f"UPDATE res_users SET company_id = 4 WHERE id = {uid}", "default co 4")

    # ====================================================================
    # VERIFICATION
    # ====================================================================
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

    remaining = [c for c in companies if c['id'] not in [4, 6]]
    if not remaining:
        print("\nSUCCESS: All demo companies deleted!")
    else:
        print(f"\nWARNING: {len(remaining)} demo companies remain")


if __name__ == '__main__':
    main()
