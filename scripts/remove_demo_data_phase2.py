#!/usr/bin/env python3
"""
Phase 2: Remove remaining demo data blocked by FK constraints.
Handles Odoo 19 model differences.
"""

import xmlrpc.client
import sys

URL = "https://odoo.emoment.tech"
DB = "odoo"
USER = "admin"
PWD = "admin"

DEMO_COMPANIES = [1, 2, 3, 5]
ALL_COMPANIES = [1, 2, 3, 4, 5, 6]
KEEP_COMPANIES = [4, 6]
DEMO_USERS = [5, 6, 11]
KEEP_EMPLOYEES = [22, 42, 43]

uid = None
models = None


def rpc(model, method, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    return models.execute_kw(DB, uid, PWD, model, method, args, kwargs)


def search(model, domain, limit=0):
    kw = {}
    if limit:
        kw['limit'] = limit
    return rpc(model, 'search', [domain], kw)


def search_read(model, domain, fields, limit=0):
    kw = {'fields': fields}
    if limit:
        kw['limit'] = limit
    return rpc(model, 'search_read', [domain], kw)


def unlink(model, ids):
    if not ids:
        return True
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        try:
            rpc(model, 'unlink', [chunk])
        except Exception as e:
            err = str(e)
            if len(err) > 200:
                err = err[:200] + "..."
            print(f"    WARN: unlink {model} chunk failed: {err}")
            for rid in chunk:
                try:
                    rpc(model, 'unlink', [[rid]])
                except Exception as e2:
                    err2 = str(e2)
                    if len(err2) > 150:
                        err2 = err2[:150] + "..."
                    print(f"    SKIP: {model} id={rid}: {err2}")
    return True


def write(model, ids, vals):
    if not ids:
        return True
    return rpc(model, 'write', [ids, vals])


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


def safe_search(model, domain):
    """Search with error handling - returns [] on failure."""
    try:
        return search(model, domain)
    except Exception as e:
        err = str(e)
        if "doesn't exist" in err or "Invalid field" in err:
            return []
        print(f"  WARN search {model}: {err[:150]}")
        return []


def safe_delete(model, domain, label=None):
    """Search and delete records matching domain."""
    label = label or model
    ids = safe_search(model, domain)
    if ids:
        print(f"  Deleting {len(ids)} {label}...")
        unlink(model, ids)
    return ids


def phase2():
    print("\n=== Phase 2: Clearing FK blockers ===\n")

    # FIRST: Restore admin access to all companies temporarily
    print("--- Restoring admin access to all companies ---")
    try:
        write('res.users', [uid], {
            'company_ids': [(6, 0, ALL_COMPANIES)],
            'company_id': 4
        })
        print("  Admin now has access to all companies")
    except Exception as e:
        print(f"  WARN: {e}")

    # 1. Delete POS data (blocks warehouses, sequences, journals, company 1)
    print("\n--- POS Data ---")
    for model_name in ['pos.order.line', 'pos.order', 'pos.session']:
        safe_delete(model_name, [('company_id', 'in', DEMO_COMPANIES)])

    safe_delete('pos.payment.method', [('company_id', 'in', DEMO_COMPANIES)])
    # Also by journal
    try:
        pm_ids = search('pos.payment.method', [('journal_id.company_id', 'in', DEMO_COMPANIES)])
        if pm_ids:
            print(f"  Deleting {len(pm_ids)} pos.payment.method (by journal)...")
            unlink('pos.payment.method', pm_ids)
    except Exception:
        pass

    safe_delete('pos.config', [('company_id', 'in', DEMO_COMPANIES)])

    # 2. Delete repair orders
    print("\n--- Repair Orders ---")
    repairs = safe_search('repair.order', [('company_id', 'in', DEMO_COMPANIES)])
    if repairs:
        for rid in repairs:
            try:
                rpc('repair.order', 'action_repair_cancel', [[rid]])
            except Exception:
                pass
        unlink('repair.order', repairs)

    # 3. Delete project updates (blocks user 5)
    print("\n--- Project Data ---")
    safe_delete('project.update', [('user_id', 'in', DEMO_USERS)])
    safe_delete('project.task', [('company_id', 'in', DEMO_COMPANIES)])
    safe_delete('project.project', [('company_id', 'in', DEMO_COMPANIES)])

    # 4. Leave allocations and leaves for demo employees
    print("\n--- Leave Data ---")
    # In Odoo 19, hr.leave.allocation may not have 'active' field
    demo_emps = safe_search('hr.employee', [('company_id', 'in', DEMO_COMPANIES)])
    demo_emps_all = list(set(demo_emps))
    print(f"  Demo employees in demo companies: {demo_emps_all}")

    if demo_emps_all:
        # Leave allocations (no active filter)
        allocs = safe_search('hr.leave.allocation', [('employee_id', 'in', demo_emps_all)])
        if allocs:
            print(f"  Resetting {len(allocs)} leave allocations to draft...")
            for aid in allocs:
                try:
                    rpc('hr.leave.allocation', 'action_draft', [[aid]])
                except Exception:
                    try:
                        write('hr.leave.allocation', [aid], {'state': 'draft'})
                    except Exception:
                        pass
            unlink('hr.leave.allocation', allocs)

        # Leave requests (no active filter)
        leaves = safe_search('hr.leave', [('employee_id', 'in', demo_emps_all)])
        if leaves:
            print(f"  Resetting {len(leaves)} leave requests to draft...")
            for lid in leaves:
                try:
                    rpc('hr.leave', 'action_draft', [[lid]])
                except Exception:
                    try:
                        write('hr.leave', [lid], {'state': 'draft'})
                    except Exception:
                        pass
            unlink('hr.leave', leaves)

    # 5. Expenses (model names differ in Odoo 19)
    print("\n--- Expenses ---")
    if demo_emps_all:
        # Try Odoo 19 expense models
        safe_delete('hr.expense', [('employee_id', 'in', demo_emps_all)])

    # 6. Delete remaining employees
    print("\n--- Remaining Demo Employees ---")
    if demo_emps_all:
        print(f"  Deleting {len(demo_emps_all)} employees: {demo_emps_all}")
        unlink('hr.employee', demo_emps_all)

    # 7. Product values blocking companies 2, 3
    print("\n--- Product Values ---")
    safe_delete('product.value', [('company_id', 'in', DEMO_COMPANIES)])
    safe_delete('product.attribute.value', [('company_id', 'in', DEMO_COMPANIES)])

    # 8. Account reconcile models blocking company 5
    print("\n--- Account Reconcile Models ---")
    rms = safe_search('account.reconcile.model', [('company_id', 'in', DEMO_COMPANIES)])
    if rms:
        safe_delete('account.reconcile.model.line', [('model_id', 'in', rms)])
        print(f"  Deleting {len(rms)} reconcile models...")
        unlink('account.reconcile.model', rms)

    # 9. Payment method lines
    print("\n--- Payment Method Lines ---")
    safe_delete('account.payment.method.line', [('company_id', 'in', DEMO_COMPANIES)])

    # 10. Remaining move lines (some were left due to tax line constraint)
    print("\n--- Remaining Account Move Lines ---")
    for company_id in DEMO_COMPANIES:
        move_lines = safe_search('account.move.line', [('company_id', '=', company_id)])
        if move_lines:
            print(f"  Company {company_id}: {len(move_lines)} move lines remaining")
            # Delete the parent moves (which cascades to lines)
            moves = safe_search('account.move', [('company_id', '=', company_id)])
            if moves:
                # Reset to draft first
                for mid in moves:
                    try:
                        rpc('account.move', 'button_draft', [[mid]])
                    except Exception:
                        pass
                print(f"  Deleting {len(moves)} moves (company {company_id})...")
                unlink('account.move', moves)

    # 11. Stock infrastructure retry
    print("\n--- Stock Infrastructure ---")
    for company_id in DEMO_COMPANIES:
        safe_delete('stock.picking.type', [('company_id', '=', company_id)],
                     f"picking types (co {company_id})")
        safe_delete('stock.rule', [('company_id', '=', company_id)],
                     f"stock rules (co {company_id})")
        safe_delete('stock.route', [('company_id', '=', company_id)],
                     f"stock routes (co {company_id})")
        safe_delete('stock.warehouse', [('company_id', '=', company_id)],
                     f"warehouses (co {company_id})")
        locs = safe_search('stock.location', [('company_id', '=', company_id)])
        if locs:
            locs.sort(reverse=True)
            print(f"  Deleting {len(locs)} locations (co {company_id})...")
            unlink('stock.location', locs)

    # 12. Journals retry
    print("\n--- Journals ---")
    for company_id in DEMO_COMPANIES:
        safe_delete('account.journal', [('company_id', '=', company_id)],
                     f"journals (co {company_id})")

    # 13. Sequences retry
    print("\n--- Sequences ---")
    for company_id in DEMO_COMPANIES:
        safe_delete('ir.sequence', [('company_id', '=', company_id)],
                     f"sequences (co {company_id})")

    # 14. Chart of accounts
    print("\n--- Accounts ---")
    for company_id in DEMO_COMPANIES:
        safe_delete('account.account', [('company_id', '=', company_id)],
                     f"accounts (co {company_id})")

    # 15. Broad sweep of remaining FK references
    print("\n--- Broad FK Sweep ---")
    sweep_models = [
        'digest.digest', 'ir.property',
        'lunch.order', 'lunch.cashmove',
        'fleet.vehicle.log.services', 'fleet.vehicle.log.fuel',
        'fleet.vehicle.log.contract', 'fleet.vehicle.odometer',
        'fleet.vehicle.assignation.log', 'fleet.vehicle',
        'event.registration', 'event.event',
        'slide.channel', 'slide.slide',
        'helpdesk.ticket', 'knowledge.article',
        'mrp.production', 'mrp.bom.line', 'mrp.bom',
        'quality.check', 'quality.alert', 'quality.point',
        'account.analytic.line', 'account.analytic.account',
        'mail.activity',
        'res.config.settings',
    ]
    for model_name in sweep_models:
        safe_delete(model_name, [('company_id', 'in', DEMO_COMPANIES)])

    # Mail activities for demo users
    safe_delete('mail.activity', [('user_id', 'in', DEMO_USERS)])

    # 16. Retry demo users
    print("\n--- Demo Users ---")
    remaining_users = safe_search('res.users', [('id', 'in', DEMO_USERS)])
    if remaining_users:
        print(f"  Deleting users: {remaining_users}")
        write('res.users', remaining_users, {'active': False})
        unlink('res.users', remaining_users)

    # 17. Delete bank accounts
    print("\n--- Bank Accounts ---")
    for company_id in DEMO_COMPANIES:
        safe_delete('res.partner.bank', [('company_id', '=', company_id)],
                     f"bank accounts (co {company_id})")

    # 18. Final company deletion attempt
    print("\n--- Company Deletion ---")
    # Restrict admin back first, then expand for deletion
    for company_id in DEMO_COMPANIES:
        exists = search('res.company', [('id', '=', company_id)])
        if not exists:
            print(f"  Company {company_id}: already deleted")
            continue

        print(f"  Company {company_id}: finding remaining blockers...")
        find_and_delete_blockers(company_id)

        try:
            unlink('res.company', [company_id])
            print(f"  Company {company_id}: DELETED")
        except Exception as e:
            err = str(e)
            if len(err) > 200:
                err = err[:200] + "..."
            print(f"  Company {company_id}: STILL BLOCKED - {err}")

    # 19. Set admin companies back to only keep companies
    print("\n--- Setting admin companies ---")
    remaining_companies = search('res.company', [('id', 'in', DEMO_COMPANIES)])
    if remaining_companies:
        # Keep access to remaining demo companies for now
        all_remaining = remaining_companies + KEEP_COMPANIES
        write('res.users', [uid], {
            'company_ids': [(6, 0, all_remaining)],
            'company_id': 4
        })
        print(f"  Admin companies set to: {all_remaining} (some demo cos still exist)")
    else:
        write('res.users', [uid], {
            'company_ids': [(6, 0, KEEP_COMPANIES)],
            'company_id': 4
        })
        print(f"  Admin companies set to: {KEEP_COMPANIES}")


def find_and_delete_blockers(company_id):
    """Find and delete remaining records blocking company deletion."""
    check_models = [
        # POS
        'pos.order.line', 'pos.order', 'pos.payment', 'pos.session',
        'pos.payment.method', 'pos.config',
        # Stock
        'stock.move.line', 'stock.move', 'stock.picking',
        'stock.quant', 'stock.lot', 'stock.scrap',
        'stock.picking.type', 'stock.rule', 'stock.route',
        'stock.warehouse.orderpoint', 'stock.warehouse', 'stock.location',
        # Sales / Purchases
        'sale.order.line', 'sale.order',
        'purchase.order.line', 'purchase.order',
        # Accounting
        'account.partial.reconcile', 'account.full.reconcile',
        'account.payment', 'account.bank.statement.line', 'account.bank.statement',
        'account.move.line', 'account.move',
        'account.reconcile.model.line', 'account.reconcile.model',
        'account.payment.method.line',
        'account.fiscal.position', 'account.tax',
        'account.journal', 'account.account',
        'account.analytic.line', 'account.analytic.account',
        # HR
        'hr.leave.allocation', 'hr.leave',
        'hr.expense', 'hr.attendance',
        'hr.employee', 'hr.department',
        # Products
        'product.value', 'product.supplierinfo',
        # CRM / Project
        'crm.lead', 'project.task', 'project.project', 'project.update',
        # Repair
        'repair.order',
        # Other
        'digest.digest', 'ir.property', 'ir.default', 'ir.sequence',
        'res.partner.bank',
        'mail.activity',
        'lunch.order',
        'fleet.vehicle',
    ]
    for model_name in check_models:
        ids = safe_search(model_name, [('company_id', '=', company_id)])
        if ids:
            print(f"    BLOCKER {model_name}: {len(ids)} records → deleting...")
            unlink(model_name, ids)


def verify():
    """Final verification."""
    print("\n\n=== FINAL VERIFICATION ===")

    companies = search_read('res.company', [], ['name'])
    print(f"\nCompanies ({len(companies)}):")
    for c in companies:
        status = "OK" if c['id'] in KEEP_COMPANIES else "SHOULD BE DELETED"
        print(f"  ID={c['id']}: {c['name']} [{status}]")

    users = search_read('res.users', [], ['login', 'name', 'active'])
    print(f"\nActive Users ({len(users)}):")
    for u in users:
        print(f"  ID={u['id']}: {u['name']} ({u['login']})")

    employees = search_read('hr.employee', [], ['name', 'company_id'])
    print(f"\nEmployees ({len(employees)}):")
    for e in employees:
        company_name = e['company_id'][1] if e['company_id'] else 'None'
        print(f"  ID={e['id']}: {e['name']} ({company_name})")

    depts = search_read('hr.department', [], ['name', 'company_id'])
    print(f"\nDepartments ({len(depts)}):")
    for d in depts:
        company_name = d['company_id'][1] if d['company_id'] else 'None'
        print(f"  ID={d['id']}: {d['name']} ({company_name})")

    admin = search_read('res.users', [('id', '=', uid)], ['company_id', 'company_ids'])
    if admin:
        print(f"\nAdmin default company: {admin[0]['company_id']}")
        print(f"Admin allowed companies: {admin[0]['company_ids']}")


def main():
    connect()
    phase2()
    verify()
    print("\n=== Phase 2 complete! ===")


if __name__ == '__main__':
    main()
