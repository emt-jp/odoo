#!/usr/bin/env python3
"""
Import Suhana Restaurant acquisition data into Odoo ERP.
Creates contacts, bank accounts, project, tasks, and uploads documents.
"""

import xmlrpc.client
import base64
import os
from pathlib import Path

# Odoo connection
URL = 'https://odoo-owxoo6vwga-an.a.run.app'
DB = 'odoo'
USER = 'admin'
PWD = 'admin'

# Document paths
SUHANA_DIR = Path('/Users/pk/Downloads/suhana')

def connect():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PWD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    print(f"Connected to Odoo as UID {uid}")
    return uid, models

def execute(models, uid, model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, PWD, model, method, *args, **kwargs)

def find_or_create_tag(models, uid, tag_name):
    """Find or create a contact tag."""
    tag_ids = execute(models, uid, 'res.partner.category', 'search',
        [[['name', '=', tag_name]]])
    if tag_ids:
        return tag_ids[0]
    return execute(models, uid, 'res.partner.category', 'create',
        [{'name': tag_name}])

def find_or_create_bank(models, uid, name, bic=False):
    """Find or create a bank."""
    bank_ids = execute(models, uid, 'res.bank', 'search',
        [[['name', '=', name]]])
    if bank_ids:
        return bank_ids[0]
    vals = {'name': name}
    if bic:
        vals['bic'] = bic
    return execute(models, uid, 'res.bank', 'create', [vals])

def upload_attachment(models, uid, name, filepath, res_model, res_id):
    """Upload a file as attachment to a record."""
    if not filepath.exists():
        print(f"  WARNING: File not found: {filepath}")
        return False
    with open(filepath, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    att_id = execute(models, uid, 'ir.attachment', 'create', [{
        'name': name,
        'datas': data,
        'res_model': res_model,
        'res_id': res_id,
        'type': 'binary',
    }])
    print(f"  Uploaded: {name} -> {res_model}/{res_id} (att_id={att_id})")
    return att_id

def create_contacts(models, uid):
    """Create seller contacts."""
    print("\n=== Creating Contacts ===")

    # Tags
    tag_suhana = find_or_create_tag(models, uid, 'Suhana Acquisition')
    tag_seller = find_or_create_tag(models, uid, 'Seller')
    print(f"Tags: Suhana={tag_suhana}, Seller={tag_seller}")

    # --- RIONA KK (Company) ---
    existing = execute(models, uid, 'res.partner', 'search',
        [[['name', 'like', 'RIONA']]])
    if existing:
        ridona_id = existing[0]
        print(f"RIONA KK already exists (id={ridona_id})")
    else:
        ridona_id = execute(models, uid, 'res.partner', 'create', [{
            'name': 'RIONA株式会社',
            'company_type': 'company',
            'is_company': True,
            'category_id': [(6, 0, [tag_suhana, tag_seller])],
            'comment': (
                'Seller company for SUHANA Indian Nepal Restaurant acquisition.\n'
                'Business License: 7北健生食き第168号\n'
                'License Valid: 2025-07-15 to 2031-07-31\n'
                'Restaurant: 東京都北区上十条五丁目14番6号\n'
                'Bank: 東京東信用金庫 両国支店, Account 4136776, Code 1320/101\n'
                'Passbook holder name: リオナ(カ'
            ),
        }])
        print(f"Created RIONA株式会社 (id={ridona_id})")

    # --- Lamichhane Dilli Raj (Individual, linked to RIONA) ---
    existing = execute(models, uid, 'res.partner', 'search',
        [[['name', 'like', 'Lamichhane']]])
    if existing:
        lamichhane_id = existing[0]
        print(f"Lamichhane already exists (id={lamichhane_id})")
    else:
        lamichhane_id = execute(models, uid, 'res.partner', 'create', [{
            'name': 'Lamichhane Dilli Raj',
            'company_type': 'person',
            'is_company': False,
            'parent_id': ridona_id,
            'category_id': [(6, 0, [tag_suhana, tag_seller])],
            'street': '東京都文京区大塚3丁目11番7-502号',
            'city': 'Tokyo',
            'country_id': execute(models, uid, 'res.country', 'search',
                [[['code', '=', 'JP']]])[0],
            'comment': (
                'Japanese name: ラミツアネ デリ ラザ\n'
                'Nationality: Nepalese\n'
                'DOB: 1985-07-20\n'
                'Residence Card #: U100660134EA\n'
                'Residence Status: 技能 (Skilled Labor)\n'
                'Residence Card Expiry: 2026-04-01\n'
                'Seller of SUHANA Indian Nepal Restaurant'
            ),
        }])
        print(f"Created Lamichhane Dilli Raj (id={lamichhane_id})")

    # --- 尾本 光洋 (License holder) ---
    existing = execute(models, uid, 'res.partner', 'search',
        [[['name', '=', '尾本 光洋']]])
    if existing:
        omoto_id = existing[0]
        print(f"尾本 光洋 already exists (id={omoto_id})")
    else:
        omoto_id = execute(models, uid, 'res.partner', 'create', [{
            'name': '尾本 光洋',
            'company_type': 'person',
            'is_company': False,
            'parent_id': ridona_id,
            'category_id': [(6, 0, [tag_suhana])],
            'comment': (
                'Business License Holder for SUHANA Indian Nepal Restaurant.\n'
                'License #: 7北健生食き第168号\n'
                'Issued by: 東京都北区保健所長\n'
                'Valid: 2025-07-15 to 2031-07-31'
            ),
        }])
        print(f"Created 尾本 光洋 (id={omoto_id})")

    # --- Bank Accounts ---
    print("\n=== Creating Bank Accounts ===")

    # Tokyo Higashi Shinkin Bank
    shinkin_bank_id = find_or_create_bank(models, uid,
        '東京東信用金庫 (Tokyo Higashi Shinkin Bank)')
    print(f"Bank: Tokyo Higashi Shinkin (id={shinkin_bank_id})")

    # Check if bank account exists for RIONA
    existing_acc = execute(models, uid, 'res.partner.bank', 'search',
        [[['acc_number', '=', '4136776'], ['partner_id', '=', ridona_id]]])
    if not existing_acc:
        execute(models, uid, 'res.partner.bank', 'create', [{
            'acc_number': '4136776',
            'partner_id': ridona_id,
            'bank_id': shinkin_bank_id,
            'acc_holder_name': 'リオナ(カ (RIONA KK)',
        }])
        print("Created bank account 4136776 for RIONA KK")
    else:
        print("Bank account 4136776 already exists for RIONA KK")

    # Japan Post Bank for Lamichhane
    yucho_bank_id = find_or_create_bank(models, uid,
        'ゆうちょ銀行 (Japan Post Bank)')
    print(f"Bank: Japan Post (id={yucho_bank_id})")

    existing_acc = execute(models, uid, 'res.partner.bank', 'search',
        [[['acc_number', '=', '5167306'], ['partner_id', '=', lamichhane_id]]])
    if not existing_acc:
        execute(models, uid, 'res.partner.bank', 'create', [{
            'acc_number': '5167306',
            'partner_id': lamichhane_id,
            'bank_id': yucho_bank_id,
            'acc_holder_name': 'ラミツアネ デリ ラザ',
        }])
        print("Created bank account 5167306 for Lamichhane")
    else:
        print("Bank account 5167306 already exists for Lamichhane")

    return ridona_id, lamichhane_id, omoto_id

def upload_documents(models, uid, ridona_id, lamichhane_id):
    """Upload all documents as attachments."""
    print("\n=== Uploading Documents ===")

    # Documents for Lamichhane
    upload_attachment(models, uid,
        'Residence Card (Front) - Lamichhane Dilli Raj',
        SUHANA_DIR / 'WhatsApp Image 2026-03-18 at 19.54.58.jpeg',
        'res.partner', lamichhane_id)

    upload_attachment(models, uid,
        'Residence Card (Back) - Lamichhane Dilli Raj',
        SUHANA_DIR / 'WhatsApp Image 2026-03-18 at 19.56.07.jpeg',
        'res.partner', lamichhane_id)

    # Documents for RIONA KK
    upload_attachment(models, uid,
        'Bank Passbook - Tokyo Higashi Shinkin (Cover)',
        SUHANA_DIR / 'suhana-bank.jpeg',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Bank Passbook - Tokyo Higashi Shinkin (Inside)',
        SUHANA_DIR / 'WhatsApp Image 2026-03-23 at 16.24.09.jpeg',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Bank Card (Back) - Tokyo Higashi Shinkin',
        SUHANA_DIR / 'WhatsApp Image 2026-03-23 at 16.24.50.jpeg',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Business License (営業許可書) - SUHANA Restaurant',
        SUHANA_DIR / 'WhatsApp Image 2026-03-23 at 16.25.20.jpeg',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Restaurant Floor Plan - SUHANA',
        SUHANA_DIR / 'WhatsApp Image 2026-03-23 at 16.25.01.jpeg',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Wise Transfer Receipt - ¥100,000 (2026-03-18)',
        SUHANA_DIR / 'transferReceipt.pdf',
        'res.partner', ridona_id)

    upload_attachment(models, uid,
        'Wise Transfer Receipt - ¥500,000 (2026-03-24)',
        SUHANA_DIR / 'transferReceipt-500.pdf',
        'res.partner', ridona_id)

def create_project(models, uid, ridona_id):
    """Create acquisition project with tasks."""
    print("\n=== Creating Project & Tasks ===")

    existing = execute(models, uid, 'project.project', 'search',
        [[['name', 'like', 'Suhana']]])
    if existing:
        project_id = existing[0]
        print(f"Project already exists (id={project_id})")
    else:
        project_id = execute(models, uid, 'project.project', 'create', [{
            'name': 'Suhana Restaurant Acquisition',
            'description': (
                'Acquisition of SUHANA Indian Nepal Restaurant\n'
                'Location: 東京都北区上十条五丁目14番6号\n'
                'Seller: RIONA株式会社 / Lamichhane Dilli Raj\n'
                'Buyer: eMoment Japan KK\n\n'
                'Payments Made:\n'
                '- 2026-03-18: ¥100,000 (Wise #2028470429)\n'
                '- 2026-03-24: ¥500,000 (Wise #2037504590)\n'
                'Total: ¥600,000\n\n'
                'Business License: 7北健生食き第168号 (valid to 2031-07-31)\n'
                'Current operator: RIONA株式会社\n'
                'License holder: 尾本 光洋'
            ),
        }])
        print(f"Created project (id={project_id})")

    # Define tasks
    tasks = [
        {
            'name': 'Business License Transfer (営業許可書)',
            'description': (
                'Transfer business license from RIONA株式会社/尾本光洋 to eMoment Japan KK.\n'
                'Current License: 7北健生食き第168号\n'
                'Valid until: 2031-07-31\n'
                'Issuer: 東京都北区保健所長\n\n'
                'Steps:\n'
                '- Contact Kita-ku Public Health Center (保健所)\n'
                '- Confirm if transfer or new application needed\n'
                '- Prepare and submit documents\n'
                '- Obtain updated license'
            ),
            'priority': '1',  # Urgent
        },
        {
            'name': 'Seller Residence Card Renewal (URGENT)',
            'description': (
                'Lamichhane Dilli Raj residence card expired 2026-04-01.\n'
                'Card #: U100660134EA\n'
                'Status: 技能 (Skilled Labor)\n\n'
                'Confirm renewal is in progress.\n'
                'Obtain updated card copy.\n'
                'Ensure seller can legally sign transfer documents.'
            ),
            'priority': '1',
        },
        {
            'name': 'Lease Agreement / Property Transfer',
            'description': (
                'Transfer lease for restaurant at 東京都北区上十条五丁目14番6号.\n\n'
                'Steps:\n'
                '- Obtain current lease agreement\n'
                '- Contact landlord about tenant change\n'
                '- Negotiate new lease under eMoment Japan KK\n'
                '- Review floor plan for renovation needs\n'
                '- Sign new lease'
            ),
            'priority': '1',
        },
        {
            'name': 'Business Transfer Agreement (売買契約書)',
            'description': (
                'Draft and execute formal purchase agreement.\n'
                'Seller: RIONA株式会社 / Lamichhane Dilli Raj\n'
                'Buyer: eMoment Japan KK\n\n'
                'Payments so far: ¥600,000\n'
                '- ¥100,000 on 2026-03-18 (Wise #2028470429)\n'
                '- ¥500,000 on 2026-03-24 (Wise #2037504590)\n\n'
                'Steps:\n'
                '- Determine total purchase price\n'
                '- Draft 売買契約書\n'
                '- Include equipment/fixture inventory\n'
                '- Legal review\n'
                '- Both parties sign\n'
                '- Complete remaining payment'
            ),
            'priority': '1',
        },
        {
            'name': 'Regulatory & Compliance',
            'description': (
                'Complete regulatory requirements:\n'
                '- Register 食品衛生責任者 (food safety supervisor)\n'
                '- Fire safety (防火管理者) confirmation\n'
                '- Tax office notification for new business activity\n'
                '- Labor insurance registration\n'
                '- Social insurance (if hiring staff)\n'
                '- Update company 定款 if needed'
            ),
            'priority': '0',
        },
        {
            'name': 'Odoo POS & Accounting Setup',
            'description': (
                'Configure Odoo for Suhana restaurant operations:\n'
                '- Set up POS for restaurant\n'
                '- Chart of Accounts (Japanese restaurant)\n'
                '- Inventory management for food supplies\n'
                '- Employee/HR module\n'
                '- Supplier/vendor records\n'
                '- Import initial transactions'
            ),
            'priority': '0',
        },
        {
            'name': 'Payment Processing Setup',
            'description': (
                'Set up payment systems for the restaurant:\n'
                '- Credit card terminal\n'
                '- QR code payments (PayPay, etc.)\n'
                '- Cash register integration with Odoo POS\n'
                '- Decide on dedicated bank account vs existing eMoment account'
            ),
            'priority': '0',
        },
    ]

    for task_data in tasks:
        existing_task = execute(models, uid, 'project.task', 'search',
            [[['name', '=', task_data['name']], ['project_id', '=', project_id]]])
        if existing_task:
            print(f"Task already exists: {task_data['name']}")
            continue
        task_id = execute(models, uid, 'project.task', 'create', [{
            'name': task_data['name'],
            'project_id': project_id,
            'description': task_data['description'],
            'priority': task_data.get('priority', '0'),
        }])
        print(f"Created task: {task_data['name']} (id={task_id})")

    return project_id

def main():
    print("=== Suhana Restaurant - Odoo Import ===\n")
    uid, models = connect()

    # 1. Create contacts & bank accounts
    ridona_id, lamichhane_id, omoto_id = create_contacts(models, uid)

    # 2. Upload documents
    upload_documents(models, uid, ridona_id, lamichhane_id)

    # 3. Create project & tasks
    project_id = create_project(models, uid, ridona_id)

    print("\n=== DONE ===")
    print(f"RIONA KK contact:      id={ridona_id}")
    print(f"Lamichhane contact:     id={lamichhane_id}")
    print(f"尾本 光洋 contact:       id={omoto_id}")
    print(f"Project:                id={project_id}")
    print(f"\nView in Odoo: {URL}/web")

if __name__ == '__main__':
    main()
