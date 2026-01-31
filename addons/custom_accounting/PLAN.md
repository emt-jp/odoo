# Japanese T-Number Invoice System Implementation Plan

## Overview
Implement the Japanese Qualified Invoice System (適格請求書等保存方式 / インボイス制度) for tax reporting compliance in Japan.

## Requirements
The Qualified Invoice System requires:
1. **T-Number Registration**: T + 13 digits (e.g., T1234567890123) for qualified invoice issuers
2. **Invoice Elements**:
   - Issuer name and T-Number
   - Transaction date
   - Description of goods/services
   - Tax rate breakdown (8% reduced / 10% standard)
   - Tax amounts by rate
   - Buyer name

## Implementation Tasks

### 1. Extend res.partner Model
- Add `t_number` field for Japan Tax Registration Number
- Add `is_qualified_invoice_issuer` boolean flag
- Add T-Number validation (T + 13 digits format)

### 2. Extend account.move Model
- Add field to track if invoice is a Qualified Invoice
- Add computed fields for tax breakdown by rate (8%/10%)
- Add validation to ensure T-Number is present for qualified invoices

### 3. Create Invoice Report Template
- Japanese-compliant invoice layout
- Display T-Number prominently
- Show tax breakdown by rate (8%/10%)
- Include all required elements per Japanese law

### 4. Add Views and Configuration
- Partner form view extension for T-Number
- Invoice form view with qualified invoice indicator
- Configuration settings for company T-Number

### 5. Security and Access
- Access rights for T-Number management
- Multi-company support

## File Structure
```
custom_accounting/
├── models/
│   ├── res_partner_t_number.py      # Partner T-Number extension
│   └── account_move_t_number.py     # Invoice T-Number extension
├── views/
│   ├── res_partner_views.xml        # Partner form extension
│   └── account_move_views.xml       # Invoice form extension
├── report/
│   └── report_invoice_t_number.xml  # Japanese invoice template
└── data/
    └── t_number_data.xml            # Default configuration
```
