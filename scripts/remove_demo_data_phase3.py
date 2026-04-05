#!/usr/bin/env python3
"""
Phase 3: Handle POS, expenses, leave allocations, and remaining blockers.
Uses direct SQL via Odoo's execute method where ORM restrictions block deletion.
"""

import xmlrpc.client
import sys

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
    return rpc(model, 'search', [domain])


def search_read(model, domain, fields):
    return rpc(model, 'search_read', [domain], {'fields': fields})


def unlink_strict(model, ids):
    """Delete records. Raises on failure."""
    if not ids:
        return
    rpc(model, 'unlink', [ids])


def unlink(model, ids):
    """Delete records with error handling."""
    if not ids:
        return
    try:
        rpc(model, 'unlink', [ids])
        print(f"    OK: {model} ({len(ids)} records)")
    except Exception as e:
        err = str(e)[:200]
        print(f"    FAIL: {model} ({len(ids)} records): {err}")
        # Try one by one
        ok = 0
        fail = 0
        for rid in ids:
            try:
                rpc(model, 'unlink', [[rid]])
                ok += 1
            except Exception:
                fail += 1
        if ok or fail:
            print(f"    Individual: {ok} deleted, {fail} failed")


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


def ensure_admin_access():
    """Make sure admin has access to all companies."""
    print("\n--- Ensuring admin access ---")
    write('res.users', [uid], {
        'company_ids': [(6, 0, ALL_COMPANIES)],
        'company_id': 4
    })
    print("  OK")


def handle_pos():
    """Properly close and delete POS data."""
    print("\n=== Handling POS Data ===")

    # Get all POS configs for demo companies
    configs = search_read('pos.config', [('company_id', 'in', DEMO_COMPANIES)], ['name', 'company_id'])
    if not configs:
        print("  No POS configs found")
        return

    print(f"  Found {len(configs)} POS configs: {[c['name'] for c in configs]}")

    # Close any open POS sessions
    sessions = search('pos.session', [('company_id', 'in', DEMO_COMPANIES), ('state', '!=', 'closed')])
    if sessions:
        print(f"  Closing {len(sessions)} open POS sessions...")
        for sid in sessions:
            try:
                rpc('pos.session', 'action_pos_session_closing_control', [[sid]])
            except Exception:
                try:
                    write('pos.session', [sid], {'state': 'closed'})
                except Exception as e:
                    print(f"    Could not close session {sid}: {str(e)[:100]}")

    # Get all POS orders
    orders = search('pos.order', [('company_id', 'in', DEMO_COMPANIES)])
    if orders:
        print(f"  Handling {len(orders)} POS orders...")
        # Need to refund/cancel them first
        for oid in orders:
            try:
                # Try action_pos_order_cancel
                rpc('pos.order', 'action_pos_order_cancel', [[oid]])
            except Exception:
                try:
                    write('pos.order', [oid], {'state': 'cancel'})
                except Exception:
                    pass

        # Now try to delete order lines
        order_lines = search('pos.order.line', [('order_id', 'in', orders)])
        if order_lines:
            unlink('pos.order.line', order_lines)

        # Delete POS payments
        try:
            payments = search('pos.payment', [('pos_order_id', 'in', orders)])
            if payments:
                unlink('pos.payment', payments)
        except Exception:
            pass

        # Delete orders
        unlink('pos.order', orders)

    # Delete remaining sessions
    all_sessions = search('pos.session', [('company_id', 'in', DEMO_COMPANIES)])
    if all_sessions:
        # Force close
        for sid in all_sessions:
            try:
                write('pos.session', [sid], {'state': 'closed'})
            except Exception:
                pass
        unlink('pos.session', all_sessions)

    # Delete POS payment methods
    pms = search('pos.payment.method', [('company_id', 'in', DEMO_COMPANIES)])
    if pms:
        unlink('pos.payment.method', pms)

    # Now try to delete POS configs
    config_ids = [c['id'] for c in configs]
    # Set configs to inactive first
    try:
        write('pos.config', config_ids, {'active': False})
    except Exception:
        pass
    unlink('pos.config', config_ids)

    # Check if any remain
    remaining = search('pos.config', [('company_id', 'in', DEMO_COMPANIES)])
    if remaining:
        print(f"  WARNING: {len(remaining)} POS configs still remain")
        # Try finding what blocks them
        for cid in remaining:
            data = search_read('pos.config', [('id', '=', cid)], ['name', 'company_id'])
            print(f"    Config {cid}: {data}")
    else:
        print("  All POS configs deleted!")


def handle_expenses():
    """Delete expenses for demo company employees."""
    print("\n=== Handling Expenses ===")

    demo_emps = search('hr.employee', [('company_id', 'in', DEMO_COMPANIES)])
    if not demo_emps:
        print("  No demo employees found")
        return

    expenses = search('hr.expense', [('employee_id', 'in', demo_emps)])
    if not expenses:
        print("  No expenses")
        return

    print(f"  Found {len(expenses)} expenses")

    # Reset to draft
    for eid in expenses:
        try:
            rpc('hr.expense', 'action_reset_expense', [[eid]])
        except Exception:
            try:
                write('hr.expense', [eid], {'state': 'draft', 'payment_mode': 'own_account'})
            except Exception:
                try:
                    write('hr.expense', [eid], {'state': 'draft'})
                except Exception as e:
                    print(f"    Could not reset expense {eid}: {str(e)[:100]}")

    # Delete
    unlink('hr.expense', expenses)


def handle_leave_allocations():
    """Delete leave allocations for demo employees."""
    print("\n=== Handling Leave Allocations ===")

    demo_emps = search('hr.employee', [('company_id', 'in', DEMO_COMPANIES)])
    if not demo_emps:
        print("  No demo employees")
        return

    allocs = search('hr.leave.allocation', [('employee_id', 'in', demo_emps)])
    if not allocs:
        print("  No leave allocations")
        return

    print(f"  Found {len(allocs)} leave allocations")

    # Reset to draft and delete
    for aid in allocs:
        try:
            rpc('hr.leave.allocation', 'action_draft', [[aid]])
        except Exception:
            try:
                write('hr.leave.allocation', [aid], {'state': 'draft'})
            except Exception:
                pass

    unlink('hr.leave.allocation', allocs)


def handle_stock_quants():
    """Clear stock quants by setting qty to 0."""
    print("\n=== Handling Stock Quants ===")

    quants = search('stock.quant', [('company_id', 'in', DEMO_COMPANIES)])
    if not quants:
        print("  No quants")
        return

    print(f"  Found {len(quants)} quants - zeroing out quantities...")
    # Can't delete quants via ORM (no unlink permission)
    # Set quantity to 0 instead
    for qid in quants:
        try:
            write('stock.quant', [qid], {'quantity': 0, 'reserved_quantity': 0})
        except Exception as e:
            print(f"    Could not zero quant {qid}: {str(e)[:100]}")


def handle_remaining_employees():
    """Delete remaining demo employees."""
    print("\n=== Handling Remaining Employees ===")

    demo_emps = search('hr.employee', [('company_id', 'in', DEMO_COMPANIES)])
    if not demo_emps:
        print("  No demo employees remaining")
        return

    print(f"  Remaining demo employees: {demo_emps}")

    # Try to archive first
    for eid in demo_emps:
        try:
            write('hr.employee', [eid], {'active': False})
        except Exception:
            pass

    unlink('hr.employee', demo_emps)

    # Check what remains
    still = search('hr.employee', [('company_id', 'in', DEMO_COMPANIES)])
    if still:
        print(f"  Still remaining: {still}")


def handle_stock_chain(company_id):
    """Delete stock infrastructure in correct order for a company."""
    print(f"\n  Stock chain for company {company_id}:")

    # 1. Stock move lines
    mls = search('stock.move.line', [('company_id', '=', company_id)])
    if mls:
        for ml in mls:
            try:
                write('stock.move.line', [ml], {'state': 'cancel'})
            except Exception:
                pass
        unlink('stock.move.line', mls)

    # 2. Stock rules → must go before picking types and warehouses
    rules = search('stock.rule', [('company_id', '=', company_id)])
    if rules:
        print(f"    {len(rules)} stock rules")
        unlink('stock.rule', rules)

    # 3. Picking types → reference locations
    pts = search('stock.picking.type', [('company_id', '=', company_id)])
    if pts:
        print(f"    {len(pts)} picking types")
        unlink('stock.picking.type', pts)

    # 4. Routes
    routes = search('stock.route', [('company_id', '=', company_id)])
    if routes:
        print(f"    {len(routes)} routes")
        unlink('stock.route', routes)

    # 5. Warehouses
    whs = search('stock.warehouse', [('company_id', '=', company_id)])
    if whs:
        print(f"    {len(whs)} warehouses")
        unlink('stock.warehouse', whs)

    # 6. Locations (children first)
    locs = search('stock.location', [('company_id', '=', company_id)])
    if locs:
        locs.sort(reverse=True)
        print(f"    {len(locs)} locations")
        unlink('stock.location', locs)


def handle_accounting_chain(company_id):
    """Delete remaining accounting infrastructure."""
    print(f"\n  Accounting chain for company {company_id}:")

    # Account groups
    try:
        groups = search('account.group', [('company_id', '=', company_id)])
        if groups:
            print(f"    {len(groups)} account groups")
            unlink('account.group', groups)
    except Exception:
        pass

    # Tax groups
    try:
        tgroups = search('account.tax.group', [('company_id', '=', company_id)])
        if tgroups:
            print(f"    {len(tgroups)} tax groups")
            unlink('account.tax.group', tgroups)
    except Exception:
        pass

    # Fiscal years / periods
    try:
        for model in ['account.fiscal.year']:
            ids = search(model, [('company_id', '=', company_id)])
            if ids:
                unlink(model, ids)
    except Exception:
        pass

    # Remaining move lines
    mls = search('account.move.line', [('company_id', '=', company_id)])
    if mls:
        print(f"    {len(mls)} remaining move lines")
        # Get parent moves
        moves = search('account.move', [('company_id', '=', company_id)])
        if moves:
            for mid in moves:
                try:
                    rpc('account.move', 'button_draft', [[mid]])
                except Exception:
                    pass
            unlink('account.move', moves)
        # Retry lines
        mls2 = search('account.move.line', [('company_id', '=', company_id)])
        if mls2:
            unlink('account.move.line', mls2)

    # Payment method lines
    try:
        pmls = search('account.payment.method.line', [('company_id', '=', company_id)])
        if pmls:
            print(f"    {len(pmls)} payment method lines")
            unlink('account.payment.method.line', pmls)
    except Exception:
        pass

    # Journals
    journals = search('account.journal', [('company_id', '=', company_id)])
    if journals:
        print(f"    {len(journals)} journals")
        unlink('account.journal', journals)

    # Taxes
    taxes = search('account.tax', [('company_id', '=', company_id)])
    if taxes:
        print(f"    {len(taxes)} taxes")
        unlink('account.tax', taxes)

    # Accounts
    accts = search('account.account', [('company_id', '=', company_id)])
    if accts:
        print(f"    {len(accts)} accounts")
        unlink('account.account', accts)

    # Reconcile models
    try:
        rms = search('account.reconcile.model', [('company_id', '=', company_id)])
        if rms:
            print(f"    {len(rms)} reconcile models")
            # Lines first
            rml = search('account.reconcile.model.line', [('model_id', 'in', rms)])
            if rml:
                unlink('account.reconcile.model.line', rml)
            unlink('account.reconcile.model', rms)
    except Exception:
        pass


def delete_companies():
    """Final company deletion."""
    print("\n=== Deleting Companies ===")

    for company_id in DEMO_COMPANIES:
        exists = search('res.company', [('id', '=', company_id)])
        if not exists:
            print(f"  Company {company_id}: already gone")
            continue

        print(f"\n--- Company {company_id} ---")
        handle_stock_chain(company_id)
        handle_accounting_chain(company_id)

        # Sequences
        seqs = search('ir.sequence', [('company_id', '=', company_id)])
        if seqs:
            print(f"  {len(seqs)} sequences")
            unlink('ir.sequence', seqs)

        # ir.property
        try:
            props = search('ir.property', [('company_id', '=', company_id)])
            if props:
                unlink('ir.property', props)
        except Exception:
            pass

        # ir.default
        try:
            defs = search('ir.default', [('company_id', '=', company_id)])
            if defs:
                unlink('ir.default', defs)
        except Exception:
            pass

        # res.config.settings
        try:
            settings = search('res.config.settings', [('company_id', '=', company_id)])
            if settings:
                unlink('res.config.settings', settings)
        except Exception:
            pass

        # Now try company
        print(f"  Attempting to delete company {company_id}...")
        try:
            unlink_strict('res.company', [company_id])
            print(f"  SUCCESS: Company {company_id} deleted!")
        except Exception as e:
            err = str(e)
            # Extract the troublemaker
            if 'troublemaker' in err:
                start = err.find("'", err.find('troublemaker'))
                end = err.find("'", start + 1) if start > 0 else -1
                model_name = err[start+1:end] if start > 0 and end > 0 else "unknown"
                print(f"  BLOCKED by: {model_name}")

                # Extract model technical name
                tech_start = err.find("(", end)
                tech_end = err.find(")", tech_start)
                if tech_start > 0 and tech_end > 0:
                    tech_name = err[tech_start+1:tech_end]
                    print(f"  Technical: {tech_name}")
                    # Try to delete those records
                    try:
                        blocking_ids = search(tech_name, [('company_id', '=', company_id)])
                        if blocking_ids:
                            print(f"  Found {len(blocking_ids)} blocking {tech_name} records, deleting...")
                            unlink(tech_name, blocking_ids)
                            # Retry
                            try:
                                unlink_strict('res.company', [company_id])
                                print(f"  SUCCESS on retry: Company {company_id} deleted!")
                            except Exception as e2:
                                print(f"  Still blocked: {str(e2)[:200]}")
                    except Exception:
                        pass
            else:
                print(f"  BLOCKED: {err[:300]}")


def set_admin_companies():
    """Set admin companies to only keep companies."""
    print("\n=== Setting Admin Companies ===")
    remaining = search('res.company', [('id', 'in', DEMO_COMPANIES)])
    if remaining:
        print(f"  Demo companies still exist: {remaining}")
        companies = remaining + KEEP_COMPANIES
    else:
        companies = KEEP_COMPANIES
    write('res.users', [uid], {
        'company_ids': [(6, 0, companies)],
        'company_id': 4
    })
    print(f"  Admin company_ids set to: {companies}")


def verify():
    print("\n\n=== FINAL VERIFICATION ===")

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
        keep = "KEEP" if e['id'] in KEEP_EMPLOYEES else "REMAINING"
        print(f"  ID={e['id']}: {e['name']} ({cn}) [{keep}]")

    admin = search_read('res.users', [('id', '=', uid)], ['company_id', 'company_ids'])
    if admin:
        print(f"\nAdmin default: {admin[0]['company_id']}")
        print(f"Admin companies: {admin[0]['company_ids']}")


def main():
    connect()
    ensure_admin_access()
    handle_pos()
    handle_expenses()
    handle_leave_allocations()
    handle_stock_quants()
    handle_remaining_employees()
    delete_companies()
    set_admin_companies()
    verify()


if __name__ == '__main__':
    main()
