#!/usr/bin/env python3
"""
Remove Odoo demo/sample data from odoo.emoment.tech.

Keeps:
  - Company 4 (eMoment Japan KK) and Company 6 (Urban Zaika)
  - Real users: Admin(2), OdooBot(1), Public(3), Portal Template(4), Prasanta(9), Prince(12), Sachiko(15)
  - Real employees: 22 (Prince), 42 (Prasanta), 43 (Prince Fleet Coordinator)
  - Departments 8-15 (company 4 departments)
  - All 154 shared products (no company_id)

Deletes:
  - Companies 1, 2, 3, 5 and ALL their transactional data
  - Demo users 5, 6, 11
  - Sample employees (1-21, 23-41, 44-56)
  - Demo departments 1-7
"""

import xmlrpc.client
import sys
import time

URL = "https://odoo.emoment.tech"
DB = "odoo"
USER = "admin"
PWD = "admin"

DEMO_COMPANIES = [1, 2, 3, 5]
COMPANIES_WITH_DATA = [1, 2, 5]  # Company 3 has no transactional data
DEMO_USERS = [5, 6, 11]
DEMO_EMPLOYEES = list(range(1, 22)) + list(range(23, 42)) + list(range(44, 57))
DEMO_DEPARTMENTS = list(range(1, 8))
KEEP_COMPANIES = [4, 6]

# Globals
uid = None
models = None


def rpc(model, method, args=None, kwargs=None):
    """Execute XML-RPC call."""
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    return models.execute_kw(DB, uid, PWD, model, method, args, kwargs)


def search(model, domain, limit=0):
    """Search for records."""
    kw = {}
    if limit:
        kw['limit'] = limit
    return rpc(model, 'search', [domain], kw)


def search_read(model, domain, fields, limit=0):
    """Search and read records."""
    kw = {'fields': fields}
    if limit:
        kw['limit'] = limit
    return rpc(model, 'search_read', [domain], kw)


def unlink(model, ids):
    """Delete records. Returns True on success."""
    if not ids:
        return True
    # Batch in chunks of 50 to avoid timeouts
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        try:
            rpc(model, 'unlink', [chunk])
        except Exception as e:
            print(f"    WARN: unlink {model} ids {chunk[:5]}... failed: {e}")
            # Try one by one
            for rid in chunk:
                try:
                    rpc(model, 'unlink', [[rid]])
                except Exception as e2:
                    print(f"    SKIP: {model} id={rid}: {e2}")
    return True


def write(model, ids, vals):
    """Update records."""
    if not ids:
        return True
    return rpc(model, 'write', [ids, vals])


def connect():
    """Connect to Odoo via XML-RPC."""
    global uid, models
    print(f"Connecting to {URL}...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', verbose=False)
    uid = common.authenticate(DB, USER, PWD, {})
    if not uid:
        print("ERROR: Authentication failed!")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', verbose=False)
    print(f"Connected as UID={uid}")
    return uid


def step1_clean_ir_defaults():
    """Step 1: Remove ir.default entries for demo companies."""
    print("\n=== Step 1: Clean ir.default entries ===")
    ids = search('ir.default', [('company_id', 'in', DEMO_COMPANIES)])
    print(f"  Found {len(ids)} ir.default entries for demo companies")
    if ids:
        unlink('ir.default', ids)
        print(f"  Deleted ir.default entries")


def step2_delete_sample_employees():
    """Step 2: Delete sample employees (not real staff)."""
    print("\n=== Step 2: Delete sample employees ===")

    # First archive them (set active=False) to detach from timesheets etc.
    existing = search('hr.employee', [('id', 'in', DEMO_EMPLOYEES), '|', ('active', '=', True), ('active', '=', False)])
    print(f"  Found {len(existing)} sample employees to delete")

    if not existing:
        print("  No sample employees found")
        return

    # Delete related records first
    # Timesheet entries
    ts_ids = search('account.analytic.line', [('employee_id', 'in', existing)])
    if ts_ids:
        print(f"  Deleting {len(ts_ids)} timesheet entries...")
        unlink('account.analytic.line', ts_ids)

    # Attendance records
    try:
        att_ids = search('hr.attendance', [('employee_id', 'in', existing)])
        if att_ids:
            print(f"  Deleting {len(att_ids)} attendance records...")
            unlink('hr.attendance', att_ids)
    except Exception:
        pass  # Module might not be installed

    # Leave allocations and requests
    try:
        alloc_ids = search('hr.leave.allocation', [('employee_id', 'in', existing), '|', ('active', '=', True), ('active', '=', False)])
        if alloc_ids:
            # Force draft then delete
            try:
                write('hr.leave.allocation', alloc_ids, {'state': 'draft'})
            except Exception:
                pass
            print(f"  Deleting {len(alloc_ids)} leave allocations...")
            unlink('hr.leave.allocation', alloc_ids)
    except Exception:
        pass

    try:
        leave_ids = search('hr.leave', [('employee_id', 'in', existing), '|', ('active', '=', True), ('active', '=', False)])
        if leave_ids:
            try:
                write('hr.leave', leave_ids, {'state': 'draft'})
            except Exception:
                pass
            print(f"  Deleting {len(leave_ids)} leave requests...")
            unlink('hr.leave', leave_ids)
    except Exception:
        pass

    # Expense records
    try:
        exp_ids = search('hr.expense', [('employee_id', 'in', existing)])
        if exp_ids:
            # Delete expense sheets first
            sheet_ids = search('hr.expense.sheet', [('employee_id', 'in', existing)])
            if sheet_ids:
                try:
                    write('hr.expense.sheet', sheet_ids, {'state': 'draft'})
                except Exception:
                    pass
                unlink('hr.expense.sheet', sheet_ids)
            print(f"  Deleting {len(exp_ids)} expense records...")
            unlink('hr.expense', exp_ids)
    except Exception:
        pass

    # Planning slots
    try:
        slot_ids = search('planning.slot', [('employee_id', 'in', existing)])
        if slot_ids:
            print(f"  Deleting {len(slot_ids)} planning slots...")
            unlink('planning.slot', slot_ids)
    except Exception:
        pass

    # Now delete the employees themselves
    print(f"  Deleting {len(existing)} employees...")
    unlink('hr.employee', existing)
    print("  Done")


def delete_stock_data(company_id):
    """Delete stock/inventory data for a company."""
    print(f"  [Stock] Company {company_id}...")

    # Cancel pickings first
    pickings = search('stock.picking', [('company_id', '=', company_id)])
    if pickings:
        print(f"    Found {len(pickings)} pickings")
        # Cancel them
        for pid in pickings:
            try:
                rpc('stock.picking', 'action_cancel', [[pid]])
            except Exception:
                pass

        # Delete stock moves
        moves = search('stock.move', [('company_id', '=', company_id)])
        if moves:
            print(f"    Deleting {len(moves)} stock moves...")
            # Force state to cancel first
            try:
                write('stock.move', moves, {'state': 'cancel'})
            except Exception:
                pass
            unlink('stock.move', moves)

        # Delete move lines
        move_lines = search('stock.move.line', [('company_id', '=', company_id)])
        if move_lines:
            print(f"    Deleting {len(move_lines)} stock move lines...")
            try:
                write('stock.move.line', move_lines, {'state': 'cancel'})
            except Exception:
                pass
            unlink('stock.move.line', move_lines)

        # Delete pickings
        print(f"    Deleting {len(pickings)} pickings...")
        try:
            write('stock.picking', pickings, {'state': 'cancel'})
        except Exception:
            pass
        unlink('stock.picking', pickings)

    # Delete quants
    quants = search('stock.quant', [('company_id', '=', company_id)])
    if quants:
        print(f"    Deleting {len(quants)} stock quants...")
        unlink('stock.quant', quants)

    # Delete lots
    lots = search('stock.lot', [('company_id', '=', company_id)])
    if lots:
        print(f"    Deleting {len(lots)} stock lots...")
        unlink('stock.lot', lots)

    # Delete scrap orders
    try:
        scraps = search('stock.scrap', [('company_id', '=', company_id)])
        if scraps:
            print(f"    Deleting {len(scraps)} scrap orders...")
            unlink('stock.scrap', scraps)
    except Exception:
        pass

    # Delete inventory adjustments
    try:
        adjusts = search('stock.inventory', [('company_id', '=', company_id)])
        if adjusts:
            unlink('stock.inventory', adjusts)
    except Exception:
        pass  # Model might not exist in v17


def delete_sale_data(company_id):
    """Delete sale orders for a company."""
    print(f"  [Sales] Company {company_id}...")

    orders = search('sale.order', [('company_id', '=', company_id)])
    if not orders:
        print("    No sale orders")
        return

    print(f"    Found {len(orders)} sale orders")

    # Cancel orders first
    for oid in orders:
        try:
            rpc('sale.order', 'action_cancel', [[oid]])
        except Exception:
            pass
    # Force state
    try:
        write('sale.order', orders, {'state': 'cancel'})
    except Exception:
        pass

    # Delete order lines
    lines = search('sale.order.line', [('company_id', '=', company_id)])
    if lines:
        print(f"    Deleting {len(lines)} sale order lines...")
        unlink('sale.order.line', lines)

    # Delete orders
    print(f"    Deleting {len(orders)} sale orders...")
    unlink('sale.order', orders)


def delete_purchase_data(company_id):
    """Delete purchase orders for a company."""
    print(f"  [Purchases] Company {company_id}...")

    orders = search('purchase.order', [('company_id', '=', company_id)])
    if not orders:
        print("    No purchase orders")
        return

    print(f"    Found {len(orders)} purchase orders")

    # Cancel orders
    for oid in orders:
        try:
            rpc('purchase.order', 'button_cancel', [[oid]])
        except Exception:
            pass
    try:
        write('purchase.order', orders, {'state': 'cancel'})
    except Exception:
        pass

    # Delete order lines
    lines = search('purchase.order.line', [('company_id', '=', company_id)])
    if lines:
        print(f"    Deleting {len(lines)} purchase order lines...")
        unlink('purchase.order.line', lines)

    # Delete orders
    print(f"    Deleting {len(orders)} purchase orders...")
    unlink('purchase.order', orders)


def delete_accounting_data(company_id):
    """Delete accounting data for a company."""
    print(f"  [Accounting] Company {company_id}...")

    # Delete payments first
    payments = search('account.payment', [('company_id', '=', company_id)])
    if payments:
        print(f"    Found {len(payments)} payments")
        # Reset to draft
        for pid in payments:
            try:
                rpc('account.payment', 'action_draft', [[pid]])
            except Exception:
                pass
        print(f"    Deleting payments...")
        unlink('account.payment', payments)

    # Delete bank statement lines
    try:
        stmt_lines = search('account.bank.statement.line', [('company_id', '=', company_id)])
        if stmt_lines:
            print(f"    Deleting {len(stmt_lines)} bank statement lines...")
            unlink('account.bank.statement.line', stmt_lines)
    except Exception:
        pass

    # Delete bank statements
    try:
        stmts = search('account.bank.statement', [('company_id', '=', company_id)])
        if stmts:
            print(f"    Deleting {len(stmts)} bank statements...")
            unlink('account.bank.statement', stmts)
    except Exception:
        pass

    # Delete partial reconciles
    try:
        partials = search('account.partial.reconcile', [('company_id', '=', company_id)])
        if partials:
            print(f"    Deleting {len(partials)} partial reconciles...")
            unlink('account.partial.reconcile', partials)
    except Exception:
        pass

    # Delete full reconciles
    try:
        fulls = search('account.full.reconcile', [('company_id', '=', company_id)])
        if fulls:
            print(f"    Deleting {len(fulls)} full reconciles...")
            unlink('account.full.reconcile', fulls)
    except Exception:
        pass

    # Now handle invoices/journal entries (account.move)
    moves = search('account.move', [('company_id', '=', company_id)])
    if moves:
        print(f"    Found {len(moves)} journal entries/invoices")

        # Reset posted entries to draft
        posted = search('account.move', [('company_id', '=', company_id), ('state', '=', 'posted')])
        if posted:
            print(f"    Resetting {len(posted)} posted entries to draft...")
            for mid in posted:
                try:
                    rpc('account.move', 'button_draft', [[mid]])
                except Exception as e:
                    # Try force-writing state
                    try:
                        write('account.move', [mid], {'state': 'draft'})
                    except Exception:
                        print(f"      WARN: Could not reset move {mid}: {e}")

        # Delete move lines first
        move_lines = search('account.move.line', [('company_id', '=', company_id)])
        if move_lines:
            print(f"    Deleting {len(move_lines)} journal entry lines...")
            unlink('account.move.line', move_lines)

        # Delete moves
        print(f"    Deleting {len(moves)} journal entries...")
        unlink('account.move', moves)


def delete_crm_data(company_id):
    """Delete CRM leads for a company."""
    print(f"  [CRM] Company {company_id}...")

    leads = search('crm.lead', [('company_id', '=', company_id)])
    if leads:
        print(f"    Deleting {len(leads)} leads...")
        unlink('crm.lead', leads)
    else:
        print("    No leads")


def delete_project_data(company_id):
    """Delete project/task data for a company."""
    print(f"  [Projects] Company {company_id}...")

    try:
        tasks = search('project.task', [('company_id', '=', company_id)])
        if tasks:
            print(f"    Deleting {len(tasks)} tasks...")
            unlink('project.task', tasks)

        projects = search('project.project', [('company_id', '=', company_id)])
        if projects:
            print(f"    Deleting {len(projects)} projects...")
            unlink('project.project', projects)
    except Exception:
        pass


def step3_delete_transactional_data():
    """Step 3: Delete all transactional data for demo companies."""
    print("\n=== Step 3: Delete transactional data ===")

    for company_id in COMPANIES_WITH_DATA:
        print(f"\n--- Company {company_id} ---")
        delete_stock_data(company_id)
        delete_sale_data(company_id)
        delete_purchase_data(company_id)
        delete_accounting_data(company_id)
        delete_crm_data(company_id)
        delete_project_data(company_id)

    # Also handle company 3 (no data expected but clean anyway)
    print(f"\n--- Company 3 (Chicago, expected empty) ---")
    delete_accounting_data(3)


def step4_delete_departments():
    """Step 4: Delete demo departments (1-7, company 1)."""
    print("\n=== Step 4: Delete demo departments ===")

    existing = search('hr.department', [('id', 'in', DEMO_DEPARTMENTS)])
    print(f"  Found {len(existing)} demo departments")
    if existing:
        unlink('hr.department', existing)
        print("  Deleted")


def step5_delete_demo_users():
    """Step 5: Delete demo users (Marc Demo, Joel Willis, Basic Employee)."""
    print("\n=== Step 5: Delete demo users ===")

    existing = search('res.users', [('id', 'in', DEMO_USERS), '|', ('active', '=', True), ('active', '=', False)])
    print(f"  Found {len(existing)} demo users")
    if existing:
        # Deactivate first
        write('res.users', existing, {'active': False})
        unlink('res.users', existing)
        print("  Deleted")


def step6_delete_company_infrastructure():
    """Step 6: Delete per-company infrastructure (warehouses, journals, companies)."""
    print("\n=== Step 6: Delete company infrastructure ===")

    for company_id in DEMO_COMPANIES:
        print(f"\n--- Company {company_id} infrastructure ---")

        # Delete stock rules
        try:
            rules = search('stock.rule', [('company_id', '=', company_id)])
            if rules:
                print(f"  Deleting {len(rules)} stock rules...")
                unlink('stock.rule', rules)
        except Exception:
            pass

        # Delete stock routes
        try:
            routes = search('stock.route', [('company_id', '=', company_id)])
            if routes:
                print(f"  Deleting {len(routes)} stock routes...")
                unlink('stock.route', routes)
        except Exception:
            pass

        # Delete orderpoints (reorder rules)
        try:
            ops = search('stock.warehouse.orderpoint', [('company_id', '=', company_id)])
            if ops:
                print(f"  Deleting {len(ops)} orderpoints...")
                unlink('stock.warehouse.orderpoint', ops)
        except Exception:
            pass

        # Delete warehouses
        warehouses = search('stock.warehouse', [('company_id', '=', company_id)])
        if warehouses:
            print(f"  Deleting {len(warehouses)} warehouses...")
            unlink('stock.warehouse', warehouses)

        # Delete stock locations
        locations = search('stock.location', [('company_id', '=', company_id)])
        if locations:
            print(f"  Deleting {len(locations)} stock locations...")
            # Delete child locations first (reverse sort by ID to get children first)
            locations.sort(reverse=True)
            unlink('stock.location', locations)

        # Delete sequences
        try:
            seqs = search('ir.sequence', [('company_id', '=', company_id)])
            if seqs:
                print(f"  Deleting {len(seqs)} sequences...")
                unlink('ir.sequence', seqs)
        except Exception:
            pass

        # Delete fiscal positions
        try:
            fps = search('account.fiscal.position', [('company_id', '=', company_id)])
            if fps:
                unlink('account.fiscal.position', fps)
        except Exception:
            pass

        # Delete tax records
        try:
            taxes = search('account.tax', [('company_id', '=', company_id)])
            if taxes:
                print(f"  Deleting {len(taxes)} tax records...")
                unlink('account.tax', taxes)
        except Exception:
            pass

        # Delete account journals
        journals = search('account.journal', [('company_id', '=', company_id)])
        if journals:
            print(f"  Deleting {len(journals)} journals...")
            unlink('account.journal', journals)

        # Delete accounts
        try:
            accounts = search('account.account', [('company_id', '=', company_id)])
            if accounts:
                print(f"  Deleting {len(accounts)} chart of accounts...")
                unlink('account.account', accounts)
        except Exception:
            pass

        # Delete bank accounts
        try:
            banks = search('res.partner.bank', [('company_id', '=', company_id)])
            if banks:
                print(f"  Deleting {len(banks)} bank accounts...")
                unlink('res.partner.bank', banks)
        except Exception:
            pass

    # Remove demo companies from admin's allowed companies
    print("\n--- Updating admin user's company access ---")
    admin_data = search_read('res.users', [('id', '=', uid)], ['company_ids'])
    if admin_data:
        current_companies = admin_data[0]['company_ids']
        new_companies = [c for c in current_companies if c in KEEP_COMPANIES]
        print(f"  Admin companies: {current_companies} → {new_companies}")
        write('res.users', [uid], {
            'company_ids': [(6, 0, new_companies)],
            'company_id': KEEP_COMPANIES[0]  # Set default to eMoment Japan KK
        })

    # Now delete the companies
    print("\n--- Deleting demo companies ---")
    for company_id in DEMO_COMPANIES:
        print(f"  Deleting company {company_id}...")
        try:
            # Delete the partner associated with the company first? No, company deletion handles it
            unlink('res.company', [company_id])
            print(f"    Done")
        except Exception as e:
            print(f"    WARN: {e}")
            # Try to find and delete remaining references
            print(f"    Trying to find remaining references...")
            try_force_delete_company(company_id)


def try_force_delete_company(company_id):
    """Try to find and remove remaining FK references blocking company deletion."""
    # Common models that reference company_id
    models_to_check = [
        'ir.property', 'ir.default', 'ir.rule',
        'mail.alias', 'mail.message', 'mail.activity',
        'res.config.settings',
        'account.analytic.plan', 'account.analytic.account',
        'account.analytic.line',
        'account.payment.method.line',
        'account.reconcile.model', 'account.reconcile.model.line',
        'digest.digest',
    ]

    for model in models_to_check:
        try:
            ids = search(model, [('company_id', '=', company_id)])
            if ids:
                print(f"    Found {len(ids)} {model} records")
                unlink(model, ids)
        except Exception:
            pass

    # Retry company deletion
    try:
        unlink('res.company', [company_id])
        print(f"    Company {company_id} deleted on retry")
    except Exception as e:
        print(f"    FAILED to delete company {company_id}: {e}")


def step7_verify():
    """Step 7: Post-cleanup verification."""
    print("\n=== Step 7: Verification ===")

    # Check remaining companies
    companies = search_read('res.company', [], ['name'])
    print(f"\n  Companies ({len(companies)}):")
    for c in companies:
        print(f"    ID={c['id']}: {c['name']}")

    # Check remaining users
    users = search_read('res.users', ['|', ('active', '=', True), ('active', '=', False)], ['login', 'name'])
    print(f"\n  Users ({len(users)}):")
    for u in users:
        print(f"    ID={u['id']}: {u['name']} ({u['login']})")

    # Check remaining employees
    employees = search_read('hr.employee', ['|', ('active', '=', True), ('active', '=', False)], ['name', 'company_id'])
    print(f"\n  Employees ({len(employees)}):")
    for e in employees:
        company_name = e['company_id'][1] if e['company_id'] else 'None'
        print(f"    ID={e['id']}: {e['name']} ({company_name})")

    # Check remaining departments
    depts = search_read('hr.department', ['|', ('active', '=', True), ('active', '=', False)], ['name', 'company_id'])
    print(f"\n  Departments ({len(depts)}):")
    for d in depts:
        company_name = d['company_id'][1] if d['company_id'] else 'None'
        print(f"    ID={d['id']}: {d['name']} ({company_name})")

    # Check admin access
    admin = search_read('res.users', [('id', '=', uid)], ['company_id', 'company_ids'])
    if admin:
        print(f"\n  Admin default company: {admin[0]['company_id']}")
        print(f"  Admin allowed companies: {admin[0]['company_ids']}")

    # Quick check for orphaned data
    for model_name in ['sale.order', 'purchase.order', 'account.move', 'stock.picking']:
        try:
            orphans = search(model_name, [('company_id', 'in', DEMO_COMPANIES)])
            if orphans:
                print(f"\n  WARNING: {len(orphans)} orphaned {model_name} records for demo companies!")
        except Exception:
            pass

    print("\n=== Cleanup complete! ===")


def main():
    connect()

    print("\n" + "="*60)
    print("  ODOO DEMO DATA REMOVAL")
    print("  Target: " + URL)
    print("  Keeping: Companies 4 (eMoment Japan KK), 6 (Urban Zaika)")
    print("  Deleting: Companies 1, 2, 3, 5 and all demo data")
    print("="*60)

    step1_clean_ir_defaults()
    step2_delete_sample_employees()
    step3_delete_transactional_data()
    step4_delete_departments()
    step5_delete_demo_users()
    step6_delete_company_infrastructure()
    step7_verify()


if __name__ == '__main__':
    main()
