# Odoo ORM System Index

## Overview
The Object-Relational Mapping (ORM) system is the core of Odoo, providing a Pythonic interface to the PostgreSQL database. It handles model definitions, field management, data persistence, and business logic execution.

## Core ORM Components

### 1. Model System (`odoo/orm/models.py`)
**Base Classes:**
- **`BaseModel`** - Abstract base class for all models
- **`Model`** - Base class for persistent models (stored in database)
- **`TransientModel`** - Base class for temporary models (wizard dialogs)
- **`AbstractModel`** - Base class for abstract models (mixins)

**Key Features:**
- Automatic table creation and management
- Inheritance mechanisms (classical and prototype)
- Method resolution order (MRO) handling
- Automatic field discovery and validation
- Recordset operations and lazy loading

### 2. Field System (`odoo/orm/fields.py` + `fields_*.py`)

#### Field Types by Category:

**Textual Fields (`fields_textual.py`):**
- **`Char`** - Short text fields
- **`Text`** - Long text fields  
- **`Html`** - Rich text with HTML formatting
- **`Monetary`** - Currency amounts

**Numeric Fields (`fields_numeric.py`):**
- **`Integer`** - Integer numbers
- **`Float`** - Decimal numbers
- **`Boolean`** - True/False values

**Temporal Fields (`fields_temporal.py`):**
- **`Date`** - Date only
- **`Datetime`** - Date and time
- **`Duration`** - Time intervals

**Binary Fields (`fields_binary.py`):**
- **`Binary`** - File attachments
- **`Image`** - Image files with automatic resizing

**Relational Fields (`fields_relational.py`):**
- **`Many2one`** - Many-to-one relationship
- **`One2many`** - One-to-many relationship
- **`Many2many`** - Many-to-many relationship

**Reference Fields (`fields_reference.py`):**
- **`Reference`** - Dynamic model reference
- **`Many2oneReference`** - Many-to-one with dynamic model

**Selection Fields (`fields_selection.py`):**
- **`Selection`** - Dropdown selection
- **`State`** - State machine fields

**Miscellaneous Fields (`fields_misc.py`):**
- **`Json`** - JSON data storage
- **`Properties`** - Dynamic properties
- **`Serialized`** - Serialized Python objects

### 3. Environment System (`odoo/orm/environments.py`)

**Environment Class:**
- **`Environment`** - Context container for ORM operations
- Contains: database cursor, user ID, context, superuser flag
- Provides model access and caching
- Manages recomputation triggers

**Transaction Management:**
- **`Transaction`** - Database transaction context
- Automatic rollback on exceptions
- Nested transaction support
- Connection pooling

### 4. Registry System (`odoo/orm/registry.py`)

**Registry Class:**
- **`Registry`** - Model registry per database
- Manages model loading and dependencies
- Handles model inheritance and overrides
- Provides model access by name

**Key Features:**
- Lazy model loading
- Model dependency resolution
- Schema management
- Model validation

### 5. API Decorators (`odoo/orm/decorators.py`)

**Method Decorators:**
- **`@api.model`** - Class methods (no recordset)
- **`@api.depends`** - Computed field dependencies
- **`@api.onchange`** - Onchange methods
- **`@api.constrains`** - Constraint validation
- **`@api.depends_context`** - Context-dependent methods
- **`@api.autovacuum`** - Automatic cleanup methods

**Field Decorators:**
- **`@api.model_create_multi`** - Multi-record creation
- **`@api.model_fields_view_get`** - View customization

### 6. Commands System (`odoo/orm/commands.py`)

**Command Types:**
- **`Command.CREATE`** - Create new records
- **`Command.UPDATE`** - Update existing records
- **`Command.DELETE`** - Delete records
- **`Command.UNLINK`** - Unlink relations
- **`Command.LINK`** - Link existing records
- **`Command.CLEAR`** - Clear all relations
- **`Command.SET`** - Set relation to specific records

### 7. Domain System (`odoo/orm/domains.py`)

**Domain Class:**
- **`Domain`** - Query condition builder
- Supports complex boolean logic
- Field path resolution
- Type checking and validation

**Operators:**
- Comparison: `=`, `!=`, `<`, `>`, `<=`, `>=`, `like`, `ilike`
- Logical: `&` (and), `|` (or), `!` (not)
- Membership: `in`, `not in`
- Null checks: `=`, `!=`

### 8. Utility System (`odoo/orm/utils.py`)

**Key Utilities:**
- **`SUPERUSER_ID`** - Superuser constant
- **`expand_ids`** - ID expansion utilities
- **`SQL_OPERATORS`** - SQL operator mapping
- **`COLLECTION_TYPES`** - Collection type definitions

## Model Definition Patterns

### Basic Model Structure
```python
from odoo import models, fields, api

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'
    
    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    
    @api.model
    def create(self, vals):
        # Custom creation logic
        return super().create(vals)
    
    def write(self, vals):
        # Custom write logic
        return super().write(vals)
```

### Field Definition Patterns
```python
# Basic fields
name = fields.Char('Name', required=True)
description = fields.Text('Description')
amount = fields.Float('Amount', digits=(16, 2))
is_active = fields.Boolean('Active', default=True)

# Relational fields
partner_id = fields.Many2one('res.partner', 'Partner')
line_ids = fields.One2many('my.model.line', 'model_id', 'Lines')
tag_ids = fields.Many2many('my.model.tag', 'model_tag_rel', 'model_id', 'tag_id', 'Tags')

# Computed fields
total_amount = fields.Float('Total Amount', compute='_compute_total_amount')
display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)

# Selection fields
state = fields.Selection([
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('done', 'Done')
], 'State', default='draft')
```

### Method Patterns
```python
@api.depends('line_ids.amount')
def _compute_total_amount(self):
    for record in self:
        record.total_amount = sum(record.line_ids.mapped('amount'))

@api.onchange('partner_id')
def _onchange_partner_id(self):
    if self.partner_id:
        self.name = self.partner_id.name

@api.constrains('amount')
def _check_amount(self):
    for record in self:
        if record.amount < 0:
            raise ValidationError("Amount must be positive")
```

## Recordset Operations

### Basic Operations
```python
# Create
record = self.env['my.model'].create({'name': 'Test'})

# Read
records = self.env['my.model'].search([('active', '=', True)])
record = self.env['my.model'].browse(1)

# Update
record.write({'name': 'Updated'})
records.write({'active': False})

# Delete
record.unlink()
```

### Search Operations
```python
# Basic search
records = self.env['my.model'].search([('name', '=', 'Test')])

# Search with domain
domain = [('state', '=', 'draft'), ('amount', '>', 100)]
records = self.env['my.model'].search(domain)

# Search with limit and order
records = self.env['my.model'].search([], limit=10, order='name desc')

# Search count
count = self.env['my.model'].search_count([('active', '=', True)])
```

### Recordset Operations
```python
# Filtering
draft_records = records.filtered(lambda r: r.state == 'draft')
confirmed_records = records.filtered('state', 'confirmed')

# Mapping
names = records.mapped('name')
amounts = records.mapped(lambda r: r.amount * 2)

# Sorting
sorted_records = records.sorted('name')
sorted_records = records.sorted(lambda r: r.amount, reverse=True)

# Grouping
grouped = records.grouped('state')
```

## Inheritance Mechanisms

### Classical Inheritance
```python
class MyModel(models.Model):
    _name = 'my.model'
    _inherit = 'mail.thread'  # Inherit from mail.thread
    
    name = fields.Char('Name')
```

### Prototype Inheritance
```python
class MyModel(models.Model):
    _name = 'my.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Add new fields
    custom_field = fields.Char('Custom Field')
    
    # Override methods
    def write(self, vals):
        # Custom logic before
        result = super().write(vals)
        # Custom logic after
        return result
```

### Field Inheritance
```python
class MyModel(models.Model):
    _inherit = 'res.partner'
    
    # Add new field
    custom_field = fields.Char('Custom Field')
    
    # Override existing field
    name = fields.Char('Name', required=False)  # Make not required
```

## Performance Considerations

### Lazy Loading
- Recordsets are lazy-loaded
- Database queries are executed only when needed
- Use `ensure_one()` for single record operations

### Caching
- Field values are cached in memory
- Use `invalidate_cache()` to clear cache
- Computed fields can be stored for performance

### Query Optimization
- Use `search()` with proper domains
- Avoid `search()` in loops
- Use `read_group()` for aggregations
- Prefetch related records when possible

### Memory Management
- Use `flush()` to persist changes
- Use `invalidate_cache()` to free memory
- Avoid large recordsets in memory

## Security and Access Control

### Access Rights
- Defined in `ir.model.access` model
- Applied automatically by ORM
- Can be bypassed with `sudo()`

### Record Rules
- Defined in `ir.rule` model
- Applied to recordset operations
- Can be bypassed with `sudo()`

### Field Access
- Fields can be restricted by groups
- Use `groups` parameter in field definition
- Access is checked during read/write operations

## Error Handling

### Common Exceptions
- **`AccessError`** - Insufficient permissions
- **`ValidationError`** - Data validation failed
- **`UserError`** - User-friendly error message
- **`MissingError`** - Record not found

### Exception Handling
```python
try:
    record.write({'name': 'Test'})
except ValidationError as e:
    # Handle validation error
    pass
except AccessError as e:
    # Handle access error
    pass
```

## Testing

### Test Model Creation
```python
def test_model_creation(self):
    record = self.env['my.model'].create({'name': 'Test'})
    self.assertEqual(record.name, 'Test')
```

### Test Field Computation
```python
def test_computed_field(self):
    record = self.env['my.model'].create({'amount': 100})
    self.assertEqual(record.total_amount, 100)
```

### Test Constraints
```python
def test_constraint(self):
    with self.assertRaises(ValidationError):
        self.env['my.model'].create({'amount': -1})
```

This ORM index provides a comprehensive overview of the Odoo ORM system, covering all major components, patterns, and best practices for working with models and data in Odoo.




