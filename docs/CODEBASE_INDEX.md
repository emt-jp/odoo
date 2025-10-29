# Odoo Codebase Index

## Overview
This is a comprehensive index of the Odoo codebase (version 19.0). Odoo is a suite of web-based open source business applications that includes CRM, Website Builder, eCommerce, Warehouse Management, Project Management, Billing & Accounting, Point of Sale, Human Resources, Marketing, Manufacturing, and more.

## Core Architecture

### Main Entry Points
- **`odoo-bin`** - Main executable script that starts the Odoo server
- **`odoo/__main__.py`** - Python module entry point
- **`odoo/init.py`** - Core initialization module with system setup and shortcuts

### Core Directories

#### `/odoo/` - Core Framework
- **`api/`** - API definitions and decorators
- **`cli/`** - Command-line interface modules
- **`fields/`** - Field type definitions
- **`models/`** - Base model definitions
- **`orm/`** - Object-Relational Mapping system
- **`service/`** - Core service implementations
- **`tools/`** - Utility functions and helpers
- **`tests/`** - Core testing framework
- **`_monkeypatches/`** - Third-party library patches

#### `/addons/` - Business Applications
Contains 200+ business modules including:
- **Core modules**: `base`, `web`, `mail`, `portal`
- **CRM**: `crm`, `crm_*` modules
- **Sales**: `sale`, `sale_*` modules  
- **Accounting**: `account`, `account_*` modules
- **Inventory**: `stock`, `delivery` modules
- **Manufacturing**: `mrp`, `mrp_*` modules
- **Human Resources**: `hr`, `hr_*` modules
- **Point of Sale**: `point_of_sale`, `pos_*` modules
- **Localization**: `l10n_*` modules for different countries
- **Payment**: `payment`, `payment_*` modules

## Core Components

### 1. ORM System (`odoo/orm/`)
The Object-Relational Mapping system is the heart of Odoo:

- **`models.py`** - Base model classes and ORM functionality
- **`fields.py`** - Field type definitions
- **`fields_*.py`** - Specific field types (binary, numeric, relational, etc.)
- **`registry.py`** - Model registry management
- **`environments.py`** - Transaction and environment management
- **`decorators.py`** - Method decorators (@api.model, @api.depends, etc.)
- **`commands.py`** - Command definitions for ORM operations

### 2. Base Module (`odoo/addons/base/`)
Core functionality required for all installations:

- **Models**: `ir_*` models for system configuration
- **Security**: Access rights, groups, and rules
- **Data**: Base data (countries, currencies, languages)
- **Views**: Core UI components and menus
- **Reports**: Base reporting functionality

### 3. Web Framework (`odoo/http.py`, `odoo/addons/web/`)
- HTTP request handling
- JSON-RPC API
- Web client framework
- Asset management

### 4. Module System (`odoo/modules/`)
- Module loading and dependency management
- Database schema management
- Migration system
- Module registry

### 5. Service Layer (`odoo/service/`)
- Database services
- Model services
- Security services
- Server management

## Key Business Modules

### Core Business Applications
- **`account`** - Accounting and financial management
- **`sale`** - Sales management
- **`purchase`** - Purchase management
- **`stock`** - Inventory management
- **`mrp`** - Manufacturing resource planning
- **`hr`** - Human resources
- **`project`** - Project management
- **`crm`** - Customer relationship management
- **`point_of_sale`** - Point of sale system
- **`website`** - Website builder
- **`ecommerce`** - E-commerce functionality

### Integration Modules
- **`mail`** - Messaging and communication
- **`portal`** - Customer portal
- **`auth_*`** - Authentication modules
- **`payment_*`** - Payment gateway integrations
- **`l10n_*`** - Localization modules

## Development Tools

### CLI Commands (`odoo/cli/`)
- **`server.py`** - Start the Odoo server
- **`shell.py`** - Interactive Python shell
- **`scaffold.py`** - Create new modules
- **`db.py`** - Database management
- **`i18n.py`** - Internationalization tools
- **`populate.py`** - Generate demo data

### Testing Framework (`odoo/tests/`)
- **`case.py`** - Base test case classes
- **`common.py`** - Common test utilities
- **`loader.py`** - Test discovery and loading
- **`suite.py`** - Test suite management

### Utilities (`odoo/tools/`)
- **`config.py`** - Configuration management
- **`convert.py`** - Data conversion utilities
- **`i18n.py`** - Internationalization tools
- **`image.py`** - Image processing
- **`pdf/`** - PDF generation
- **`sql.py`** - SQL utilities
- **`translate.py`** - Translation tools

## File Structure Patterns

### Module Structure
Each addon module typically contains:
- **`__manifest__.py`** - Module metadata and dependencies
- **`__init__.py`** - Module initialization
- **`models/`** - Data models
- **`views/`** - User interface definitions
- **`security/`** - Access rights and security rules
- **`data/`** - Initial data and demo data
- **`static/`** - Static assets (CSS, JS, images)
- **`tests/`** - Module-specific tests
- **`wizard/`** - Wizard dialogs
- **`i18n/`** - Translation files

### Model Structure
- Models inherit from `odoo.models.Model`
- Fields are defined as class attributes
- Methods use decorators for API specification
- Views are defined in XML files
- Security is defined in CSV and XML files

## Key Technologies

### Backend
- **Python 3.10+** - Main programming language
- **PostgreSQL** - Primary database
- **Psycopg2** - Database adapter
- **Werkzeug** - WSGI framework
- **Jinja2** - Template engine

### Frontend
- **JavaScript** - Client-side programming
- **QWeb** - Template engine
- **SCSS/SASS** - CSS preprocessing
- **Bootstrap** - UI framework

### Dependencies
- **LXML** - XML processing
- **Pillow** - Image processing
- **ReportLab** - PDF generation
- **Num2words** - Number to text conversion
- **Babel** - Internationalization
- **Requests** - HTTP client

## Configuration

### Main Configuration Files
- **`setup.py`** - Python package configuration
- **`requirements.txt`** - Python dependencies
- **`ruff.toml`** - Code linting configuration
- **`setup.cfg`** - Additional package configuration

### Database Configuration
- Database settings in `odoo/service/db.py`
- Connection management in `odoo/sql_db.py`
- Migration scripts in `odoo/upgrade_code/`

## Security

### Access Control
- **Groups and Users** - Defined in `res_groups` and `res_users` models
- **Access Rights** - Defined in `ir.model.access` model
- **Record Rules** - Defined in `ir.rule` model
- **Menu Security** - Controlled by group membership

### Authentication
- Multiple authentication methods supported
- OAuth, LDAP, TOTP, and password policies
- API key authentication
- Session management

## Internationalization

### Translation System
- **PO files** - Translation files in `i18n/` directories
- **Language management** - Supported languages in `res_lang` model
- **Currency support** - Multi-currency support
- **Date/time formatting** - Locale-specific formatting

## Performance

### Caching
- Multi-level caching system
- Model-level caching
- View caching
- Asset bundling and minification

### Database Optimization
- Index management
- Query optimization
- Connection pooling
- Lazy loading

## Development Guidelines

### Code Style
- Follows PEP 8 with Odoo-specific conventions
- Uses Ruff for linting
- Type hints where appropriate
- Comprehensive docstrings

### Testing
- Unit tests for models and business logic
- Integration tests for workflows
- UI tests for user interactions
- Performance tests for critical paths

## Version Information
- **Current Version**: 19.0.0 (Final)
- **Python Requirements**: 3.10 - 3.13
- **PostgreSQL Requirements**: 13+
- **License**: LGPL-3

This index provides a comprehensive overview of the Odoo codebase structure and organization. For specific implementation details, refer to the individual module documentation and source code.




