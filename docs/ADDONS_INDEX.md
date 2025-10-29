# Odoo Addons Structure Index

## Overview
Odoo includes 200+ business modules (addons) that provide comprehensive business functionality. These modules are organized by business domain and can be installed independently or as part of complete business suites.

## Core Business Applications

### 1. Accounting & Finance (`account` + related modules)
**Main Module:** `account` - Invoicing & Payments
- **Purpose:** Complete accounting and financial management
- **Key Features:** Invoicing, payments, bank reconciliation, financial reporting
- **Dependencies:** `base_setup`, `onboarding`, `product`, `analytic`, `portal`, `digest`

**Related Modules:**
- `account_check_printing` - Check printing
- `account_debit_note` - Debit notes
- `account_edi` - Electronic Data Interchange
- `account_payment` - Payment processing
- `account_tax_python` - Tax calculations
- `analytic` - Analytic accounting
- `l10n_*` - Localization modules for different countries

### 2. Sales Management (`sale` + related modules)
**Main Module:** `sale` - Sales internal machinery
- **Purpose:** Sales order management and processing
- **Key Features:** Quotations, sales orders, invoicing, customer management
- **Dependencies:** `sales_team`, `account_payment`, `utm`

**Related Modules:**
- `crm` - Customer Relationship Management
- `sales_team` - Sales team management
- `sale_crm` - CRM integration
- `sale_mrp` - Manufacturing integration
- `sale_project` - Project integration
- `sale_stock` - Inventory integration

### 3. Customer Relationship Management (`crm` + related modules)
**Main Module:** `crm` - Track leads and close opportunities
- **Purpose:** Lead and opportunity management
- **Key Features:** Lead tracking, opportunity management, sales pipeline
- **Dependencies:** `base_setup`, `sales_team`, `mail`, `calendar`, `resource`, `utm`

**Related Modules:**
- `crm_iap_enrich` - Lead enrichment
- `crm_iap_mine` - Lead mining
- `crm_livechat` - Live chat integration
- `crm_mail_plugin` - Email integration
- `crm_sms` - SMS integration

### 4. Inventory Management (`stock` + related modules)
**Main Module:** `stock` - Inventory
- **Purpose:** Stock and logistics management
- **Key Features:** Inventory tracking, warehouse management, stock moves
- **Dependencies:** `product`, `barcodes_gs1_nomenclature`, `digest`

**Related Modules:**
- `delivery` - Delivery management
- `purchase_stock` - Purchase integration
- `sale_stock` - Sales integration
- `stock_account` - Accounting integration
- `stock_landed_costs` - Landed costs
- `stock_picking_batch` - Batch operations

### 5. Manufacturing (`mrp` + related modules)
**Main Module:** `mrp` - Manufacturing
- **Purpose:** Manufacturing resource planning
- **Key Features:** Bill of materials, work orders, production planning
- **Dependencies:** `stock`, `product`, `purchase`

**Related Modules:**
- `mrp_account` - Accounting integration
- `mrp_landed_costs` - Landed costs
- `mrp_repair` - Repair management
- `mrp_subcontracting` - Subcontracting
- `mrp_workorder` - Work order management

### 6. Human Resources (`hr` + related modules)
**Main Module:** `hr` - Employees
- **Purpose:** Human resource management
- **Key Features:** Employee management, organizational structure
- **Dependencies:** `base_setup`, `digest`, `phone_validation`, `resource_mail`, `web`

**Related Modules:**
- `hr_attendance` - Attendance tracking
- `hr_expense` - Expense management
- `hr_holidays` - Leave management
- `hr_payroll` - Payroll management
- `hr_recruitment` - Recruitment
- `hr_timesheet` - Timesheet management
- `hr_skills` - Skills management

### 7. Point of Sale (`point_of_sale` + related modules)
**Main Module:** `point_of_sale` - Point of Sale
- **Purpose:** Retail and restaurant point of sale
- **Key Features:** Checkout, payments, receipts, inventory integration
- **Dependencies:** `resource`, `stock_account`, `barcodes`, `html_editor`, `digest`

**Related Modules:**
- `pos_restaurant` - Restaurant management
- `pos_loyalty` - Loyalty programs
- `pos_discount` - Discount management
- `pos_hr` - HR integration
- `pos_sale` - Sales integration

### 8. Project Management (`project` + related modules)
**Main Module:** `project` - Project
- **Purpose:** Project and task management
- **Key Features:** Project planning, task tracking, time management
- **Dependencies:** `base_setup`, `mail`, `portal`, `web_tour`, `digest`

**Related Modules:**
- `project_account` - Accounting integration
- `project_hr` - HR integration
- `project_mrp` - Manufacturing integration
- `project_purchase` - Purchase integration
- `project_sale` - Sales integration
- `project_stock` - Inventory integration

### 9. Website & eCommerce (`website` + related modules)
**Main Module:** `website` - Website Builder
- **Purpose:** Website creation and management
- **Key Features:** Drag-and-drop website builder, SEO, multi-language
- **Dependencies:** `web`, `portal`, `digest`

**Related Modules:**
- `website_sale` - eCommerce
- `website_blog` - Blog management
- `website_forum` - Forum management
- `website_slides` - eLearning
- `website_event` - Event management
- `website_livechat` - Live chat

### 10. Marketing (`mass_mailing` + related modules)
**Main Module:** `mass_mailing` - Email Marketing
- **Purpose:** Marketing campaign management
- **Key Features:** Email campaigns, newsletters, marketing automation
- **Dependencies:** `mail`, `utm`, `web`

**Related Modules:**
- `mass_mailing_crm` - CRM integration
- `mass_mailing_event` - Event integration
- `mass_mailing_sale` - Sales integration
- `mass_mailing_sms` - SMS integration
- `social_media` - Social media management

## Module Categories

### Core Modules
- `base` - Core functionality (auto-installed)
- `web` - Web client framework
- `mail` - Messaging and communication
- `portal` - Customer portal
- `digest` - Digest emails
- `onboarding` - Onboarding system

### Sales & CRM
- `crm` - Customer Relationship Management
- `sale` - Sales Management
- `sales_team` - Sales Team Management
- `utm` - UTM tracking
- `phone_validation` - Phone number validation
- `partner_autocomplete` - Partner data enrichment

### Accounting & Finance
- `account` - Accounting
- `account_payment` - Payment processing
- `analytic` - Analytic accounting
- `l10n_*` - Localization modules

### Inventory & Manufacturing
- `stock` - Inventory Management
- `mrp` - Manufacturing
- `delivery` - Delivery Management
- `purchase` - Purchase Management
- `product` - Product Management

### Human Resources
- `hr` - Human Resources
- `hr_attendance` - Attendance
- `hr_expense` - Expense Management
- `hr_holidays` - Leave Management
- `hr_recruitment` - Recruitment
- `hr_timesheet` - Timesheet

### Point of Sale
- `point_of_sale` - Point of Sale
- `pos_restaurant` - Restaurant Management
- `pos_loyalty` - Loyalty Programs
- `pos_hr` - HR Integration

### Project Management
- `project` - Project Management
- `project_account` - Accounting Integration
- `project_hr` - HR Integration
- `project_sale` - Sales Integration

### Website & eCommerce
- `website` - Website Builder
- `website_sale` - eCommerce
- `website_blog` - Blog
- `website_forum` - Forum
- `website_slides` - eLearning

### Marketing
- `mass_mailing` - Email Marketing
- `social_media` - Social Media
- `utm` - UTM Tracking
- `digest` - Digest Emails

### Communication
- `mail` - Messaging
- `mail_bot` - Mail Bot
- `im_livechat` - Live Chat
- `sms` - SMS
- `voip` - VoIP

### Authentication & Security
- `auth_oauth` - OAuth Authentication
- `auth_ldap` - LDAP Authentication
- `auth_totp` - TOTP Authentication
- `auth_password_policy` - Password Policy

### Payment Gateways
- `payment_adyen` - Adyen
- `payment_paypal` - PayPal
- `payment_stripe` - Stripe
- `payment_razorpay` - Razorpay
- `payment_authorize` - Authorize.net

### Localization (`l10n_*`)
- `l10n_us` - United States
- `l10n_fr` - France
- `l10n_de` - Germany
- `l10n_uk` - United Kingdom
- `l10n_in` - India
- `l10n_br` - Brazil
- `l10n_mx` - Mexico
- And 100+ more country-specific modules

## Module Structure

### Standard Module Structure
Each module typically contains:
```
module_name/
├── __init__.py              # Module initialization
├── __manifest__.py          # Module metadata
├── models/                  # Data models
│   ├── __init__.py
│   └── *.py
├── views/                   # User interface
│   └── *.xml
├── security/                # Access rights
│   ├── *.xml
│   └── ir.model.access.csv
├── data/                    # Initial data
│   └── *.xml
├── demo/                    # Demo data
│   └── *.xml
├── static/                  # Static assets
│   ├── src/
│   ├── description/
│   └── tests/
├── tests/                   # Unit tests
│   └── *.py
├── wizard/                  # Wizard dialogs
│   └── *.xml
├── i18n/                    # Translations
│   └── *.po
└── report/                  # Reports
    └── *.xml
```

### Manifest File Structure
```python
{
    'name': 'Module Name',
    'version': '1.0',
    'category': 'Category/Subcategory',
    'summary': 'Short description',
    'description': 'Long description',
    'depends': ['module1', 'module2'],
    'data': ['file1.xml', 'file2.xml'],
    'demo': ['demo_file.xml'],
    'assets': {
        'web.assets_backend': ['static/src/css/style.css'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'author': 'Author Name',
    'license': 'LGPL-3',
}
```

## Module Dependencies

### Dependency Types
1. **Hard Dependencies** - Required for module to function
2. **Soft Dependencies** - Optional, provides additional features
3. **Auto-install** - Automatically installed with dependencies

### Common Dependency Patterns
- All modules depend on `base`
- Business modules depend on `web`
- Communication modules depend on `mail`
- Portal modules depend on `portal`
- Localization modules depend on `account`

## Module Installation

### Installation Process
1. **Dependency Resolution** - Install required modules
2. **Data Loading** - Load initial data and demo data
3. **Schema Creation** - Create database tables
4. **View Loading** - Load user interface definitions
5. **Security Setup** - Configure access rights
6. **Post-init Hooks** - Run module-specific initialization

### Module States
- **Uninstalled** - Not installed
- **To Install** - Queued for installation
- **Installed** - Currently installed
- **To Upgrade** - Queued for upgrade
- **To Remove** - Queued for removal

## Customization and Extension

### Inheritance Mechanisms
1. **Model Inheritance** - Extend existing models
2. **View Inheritance** - Modify existing views
3. **Controller Inheritance** - Extend web controllers
4. **Asset Inheritance** - Extend CSS/JS assets

### Custom Module Creation
1. Create module directory
2. Add `__manifest__.py` with metadata
3. Define models in `models/` directory
4. Create views in `views/` directory
5. Set up security in `security/` directory
6. Add initial data in `data/` directory

## Testing

### Test Types
1. **Unit Tests** - Test individual methods
2. **Integration Tests** - Test module interactions
3. **UI Tests** - Test user interface
4. **Performance Tests** - Test performance

### Test Structure
- Tests in `tests/` directory
- Test classes inherit from `odoo.tests.common.TransactionCase`
- Use `@odoo.tests.tagged()` for test categorization

## Performance Considerations

### Module Loading
- Lazy loading of modules
- Dependency caching
- Asset bundling and minification

### Database Optimization
- Proper indexing
- Query optimization
- Connection pooling

### Memory Management
- Efficient data structures
- Proper cleanup
- Resource management

This addons index provides a comprehensive overview of the Odoo module ecosystem, covering all major business applications, their relationships, and best practices for working with them.




