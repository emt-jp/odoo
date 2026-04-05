#!/usr/bin/env python3
"""
Convert Rakuten Bank and Wise CSV statements to Odoo bank statement format,
then import via XML-RPC.

Usage:
  python3 bank-import.py rakuten /path/to/rakuten.csv
  python3 bank-import.py wise /path/to/wise.pdf   (uses the exported activities PDF - must convert first)
  python3 bank-import.py wise-csv /path/to/wise.csv  (if Wise CSV export available)
"""

import csv
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path

URL = 'https://odoo-owxoo6vwga-an.a.run.app'
DB = 'odoo'
USER = 'admin'
PWD = 'admin'

JOURNAL_RAKUTEN = 39  # 楽天銀行
JOURNAL_WISE = 40     # Wise

def connect():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PWD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    return uid, models

def parse_rakuten_csv(filepath):
    """
    Rakuten Bank CSV format:
    "Value Date","Description","Debit","Credit","Balance","Memo"
    "2026/01/01","税引前利息","","4","24962",""

    Debit = money OUT (expense/transfer), Credit = money IN (income/deposit)
    """
    lines = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row['Value Date'].strip('"')
            date = datetime.strptime(date_str, '%Y/%m/%d').strftime('%Y-%m-%d')

            debit = row.get('Debit', '').strip().strip('"')
            credit = row.get('Credit', '').strip().strip('"')

            if credit and credit != '':
                amount = float(credit)
            elif debit and debit != '':
                amount = -float(debit)
            else:
                continue

            description = row.get('Description', '').strip().strip('"')
            memo = row.get('Memo', '').strip().strip('"')
            label = f"{description} {memo}".strip()

            lines.append({
                'date': date,
                'payment_ref': label,
                'amount': amount,
            })

    # Reverse to chronological order (Rakuten CSV is newest first)
    lines.reverse()
    return lines

def parse_wise_csv(filepath):
    """
    Wise CSV export format (from wise.com > Statements > CSV):
    TransferWise ID,Date,Amount,Currency,Description,Payment Reference,Running Balance,Exchange From,Exchange To,...

    If not available, use the PDF exported activities and manually convert.
    For now, support a simple format:
    Date,Description,Amount,Fee,Currency
    """
    lines = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        for row in reader:
            # Try Wise's standard CSV format
            if 'Date' in headers and 'Amount' in headers:
                date_str = row.get('Date', '').strip()
                # Wise dates can be various formats
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y']:
                    try:
                        date = datetime.strptime(date_str[:10], fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                else:
                    print(f"  SKIP: Cannot parse date '{date_str}'")
                    continue

                amount_str = row.get('Amount', '0').strip().replace(',', '')
                amount = float(amount_str)

                desc = row.get('Description', '').strip()
                ref = row.get('Payment Reference', '').strip()
                label = f"{desc} {ref}".strip() if ref else desc

                lines.append({
                    'date': date,
                    'payment_ref': label,
                    'amount': amount,
                })

    return lines

def import_to_odoo(uid, models, journal_id, lines, statement_name):
    """Create bank statement in Odoo with parsed lines."""
    if not lines:
        print("No lines to import!")
        return

    # Group by month for statement name
    first_date = lines[0]['date']
    last_date = lines[-1]['date']

    print(f"\nImporting {len(lines)} transactions to journal {journal_id}")
    print(f"Date range: {first_date} to {last_date}")

    # Create bank statement
    stmt_id = models.execute_kw(DB, uid, PWD, 'account.bank.statement', 'create', [{
        'name': statement_name,
        'journal_id': journal_id,
        'date': last_date,
    }])
    print(f"Created statement: {statement_name} (id={stmt_id})")

    # Create statement lines
    for i, line in enumerate(lines):
        line_id = models.execute_kw(DB, uid, PWD, 'account.bank.statement.line', 'create', [{
            'statement_id': stmt_id,
            'journal_id': journal_id,
            'date': line['date'],
            'payment_ref': line['payment_ref'],
            'amount': line['amount'],
        }])
        if (i + 1) % 20 == 0:
            print(f"  Imported {i+1}/{len(lines)} lines...")

    print(f"  Imported all {len(lines)} lines")
    return stmt_id

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python3 bank-import.py rakuten /path/to/rakuten.csv")
        print("  python3 bank-import.py wise-csv /path/to/wise.csv")
        sys.exit(1)

    bank_type = sys.argv[1]
    filepath = sys.argv[2]
    statement_name = sys.argv[3] if len(sys.argv) > 3 else None

    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    uid, models = connect()
    print(f"Connected to Odoo (uid={uid})")

    if bank_type == 'rakuten':
        lines = parse_rakuten_csv(filepath)
        journal_id = JOURNAL_RAKUTEN
        if not statement_name:
            statement_name = f"楽天銀行 {Path(filepath).stem}"
    elif bank_type in ('wise', 'wise-csv'):
        lines = parse_wise_csv(filepath)
        journal_id = JOURNAL_WISE
        if not statement_name:
            statement_name = f"Wise {Path(filepath).stem}"
    else:
        print(f"Unknown bank type: {bank_type}")
        sys.exit(1)

    print(f"Parsed {len(lines)} transactions from {filepath}")
    if lines:
        print(f"Sample: {lines[0]}")
        print(f"Sample: {lines[-1]}")

    # Confirm before importing
    response = input(f"\nImport {len(lines)} lines to Odoo? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)

    stmt_id = import_to_odoo(uid, models, journal_id, lines, statement_name)
    print(f"\nDone! Statement ID: {stmt_id}")
    print(f"View: {URL}/web#action=account.action_bank_statement_tree&id={stmt_id}")

if __name__ == '__main__':
    main()
