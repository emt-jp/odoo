# Car Rental & Fleet Management - UI/UX Design System

**Version:** 2.0.0
**Last Updated:** 2025-12-29
**Scope:** car_rental_fleet, hr_payroll_custom, hr_fleet_integration

---

## 1. Design Principles

### Core Values
- **Clarity First**: Information should be instantly understandable
- **Visual Hierarchy**: Important data prominently displayed
- **Consistency**: Same patterns across all modules
- **Responsiveness**: Works on all screen sizes
- **Accessibility**: WCAG 2.1 AA compliance

---

## 2. Color System & Status Indicators

### Primary Status Colors

| Status | Color Class | Hex Code | Usage |
|--------|------------|----------|-------|
| **Success** | `decoration-success` | #28a745 | Available, Valid, Completed, Approved |
| **Info** | `decoration-info` | #17a2b8 | Reserved, On Trip, In Progress, Pending |
| **Warning** | `decoration-warning` | #ffc107 | Maintenance, Expiring Soon (≤30 days), Attention Needed |
| **Danger** | `decoration-danger` | #dc3545 | Rented, Out of Service, Expired, Overdue, Failed |
| **Muted** | `decoration-muted` | #6c757d | Sold, Not Available, Suspended, Cancelled, Archived |

### Status-to-Color Mapping

#### Fleet Vehicle Status
```xml
<field name="availability_status" widget="badge"
       decoration-success="availability_status == 'available'"
       decoration-info="availability_status == 'reserved'"
       decoration-warning="availability_status == 'maintenance'"
       decoration-danger="availability_status in ('rented', 'out_of_service')"
       decoration-muted="availability_status == 'sold'"/>
```

#### Booking Status
```xml
<field name="state" widget="badge"
       decoration-muted="state == 'draft'"
       decoration-info="state == 'confirmed'"
       decoration-success="state == 'assigned'"
       decoration-danger="state == 'cancelled'"/>
```

#### Rental Status
```xml
<field name="state" widget="badge"
       decoration-muted="state == 'draft'"
       decoration-info="state in ('confirmed', 'in_progress')"
       decoration-success="state == 'completed'"
       decoration-danger="state == 'cancelled'"/>
```

#### Maintenance Priority
```xml
<field name="priority" widget="badge"
       decoration-danger="priority == 'urgent'"
       decoration-warning="priority == 'high'"
       decoration-info="priority == 'normal'"
       decoration-muted="priority == 'low'"/>
```

#### Payment Status
```xml
<field name="payment_status" widget="badge"
       decoration-danger="payment_status == 'overdue'"
       decoration-warning="payment_status == 'pending'"
       decoration-info="payment_status == 'partial'"
       decoration-success="payment_status == 'paid'"/>
```

#### Document Expiration
```xml
<field name="days_to_expiry" widget="badge"
       decoration-danger="is_expired"
       decoration-warning="days_to_expiry &lt;= 30 and days_to_expiry &gt; 0"
       decoration-success="days_to_expiry &gt; 30"/>
```

#### Damage Severity
```xml
<field name="severity" widget="badge"
       decoration-danger="severity == 'severe'"
       decoration-warning="severity in ('major', 'moderate')"
       decoration-info="severity == 'minor'"/>
```

#### Driver Status
```xml
<field name="driver_license_state" widget="badge"
       decoration-success="driver_license_state == 'valid'"
       decoration-warning="driver_license_state == 'expiring_soon'"
       decoration-danger="driver_license_state in ('expired', 'revoked')"
       decoration-muted="driver_license_state == 'suspended'"/>
```

#### Payroll Status
```xml
<field name="state" widget="badge"
       decoration-muted="state == 'draft'"
       decoration-info="state == 'verify'"
       decoration-success="state == 'done'"
       decoration-danger="state == 'cancel'"/>
```

---

## 3. Badge & Widget Guidelines

### When to Use Badge Widget
- **Always** for status fields (state, availability, priority)
- **Always** for boolean-like selections (yes/no, active/inactive)
- **Always** for severity/urgency indicators

### Badge Best Practices
```xml
<!-- ✅ GOOD: Clear labeling, proper widget, decorations -->
<field name="availability_status" string="Status"
       widget="badge" optional="show"
       decoration-success="availability_status == 'available'"
       decoration-danger="availability_status == 'rented'"/>

<!-- ❌ BAD: No widget, no decorations, unclear label -->
<field name="availability_status"/>
```

### Special Badge Types

#### Countdown Badges (Expiration)
```xml
<field name="days_to_expiry" string="Days Left" widget="badge"
       decoration-danger="is_expired"
       decoration-warning="days_to_expiry &lt;= 30 and days_to_expiry &gt; 0"
       decoration-success="days_to_expiry &gt; 30"/>
```

#### Monetary Badges
```xml
<field name="total_amount" widget="monetary"
       decoration-success="payment_status == 'paid'"
       decoration-danger="payment_status == 'overdue'"/>
```

#### Progress Badges
```xml
<field name="completion_percentage" widget="progressbar"
       decoration-success="completion_percentage == 100"
       decoration-warning="completion_percentage &lt; 50"/>
```

---

## 4. Icon System

### Standard Icons (Font Awesome)

#### Entity Icons
| Entity | Icon Class | Example |
|--------|-----------|---------|
| Vehicle | `fa-car` | <i class="fa fa-car"></i> |
| Booking | `fa-calendar` | <i class="fa fa-calendar"></i> |
| Rental | `fa-calendar-check-o` | <i class="fa fa-calendar-check-o"></i> |
| Maintenance | `fa-wrench` | <i class="fa fa-wrench"></i> |
| Insurance | `fa-shield` | <i class="fa fa-shield"></i> |
| Driver | `fa-user` | <i class="fa fa-user"></i> |
| Documents | `fa-file-text-o` | <i class="fa fa-file-text-o"></i> |
| GPS Tracking | `fa-map-marker` | <i class="fa fa-map-marker"></i> |
| Fuel | `fa-tint` | <i class="fa fa-tint"></i> |
| Damage | `fa-exclamation-triangle` | <i class="fa fa-exclamation-triangle"></i> |
| Payment | `fa-money` | <i class="fa fa-money"></i> |
| Payroll | `fa-calculator` | <i class="fa fa-calculator"></i> |
| Contract | `fa-file-text` | <i class="fa fa-file-text"></i> |

#### Action Icons
| Action | Icon Class | Example |
|--------|-----------|---------|
| Add/Create | `fa-plus` | <i class="fa fa-plus"></i> |
| Edit | `fa-pencil` | <i class="fa fa-pencil"></i> |
| Delete | `fa-trash` | <i class="fa fa-trash"></i> |
| View | `fa-eye` | <i class="fa fa-eye"></i> |
| Download | `fa-download` | <i class="fa fa-download"></i> |
| Upload | `fa-upload` | <i class="fa fa-upload"></i> |
| Print | `fa-print` | <i class="fa fa-print"></i> |
| Search | `fa-search` | <i class="fa fa-search"></i> |
| Filter | `fa-filter` | <i class="fa fa-filter"></i> |
| Settings | `fa-cog` | <i class="fa fa-cog"></i> |

#### Status Icons
| Status | Icon Class | Example |
|--------|-----------|---------|
| Success | `fa-check-circle` | <i class="fa fa-check-circle"></i> |
| Warning | `fa-exclamation-circle` | <i class="fa fa-exclamation-circle"></i> |
| Error | `fa-times-circle` | <i class="fa fa-times-circle"></i> |
| Info | `fa-info-circle` | <i class="fa fa-info-circle"></i> |

### Icon Usage in Views

#### Kanban Cards
```xml
<i class="fa fa-car"/> <field name="model_id"/>
<i class="fa fa-calendar"/> <field name="pickup_date"/>
```

#### Stat Buttons
```xml
<button name="action_view_documents" type="object" class="oe_stat_button" icon="fa-file-text-o">
    <field name="document_count" widget="statinfo" string="Documents"/>
</button>
```

#### Menu Items
```xml
<menuitem id="menu_fleet_vehicles"
          name="Vehicles"
          web_icon="car_rental_fleet,static/description/icon.png"/>
```

---

## 5. Form Layout Patterns

### Standard Form Structure
```xml
<form string="Entity Name">
    <header>
        <!-- Status bar and action buttons -->
        <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,completed"/>
        <button name="action_confirm" string="Confirm" type="object" class="oe_highlight"/>
    </header>
    <sheet>
        <!-- Button box for stat buttons (if applicable) -->
        <div class="oe_button_box" name="button_box">
            <button name="action_view_related" type="object" class="oe_stat_button" icon="fa-item">
                <field name="related_count" widget="statinfo" string="Related"/>
            </button>
        </div>

        <!-- Title (for important entities) -->
        <div class="oe_title">
            <h1><field name="name" placeholder="Entity Name"/></h1>
        </div>

        <!-- Main information in grouped sections -->
        <group>
            <group string="Primary Information">
                <field name="field1"/>
                <field name="field2"/>
            </group>
            <group string="Secondary Information">
                <field name="field3"/>
                <field name="field4"/>
            </group>
        </group>

        <!-- Additional details in tabs -->
        <notebook>
            <page string="Details" name="details">
                <!-- Detail content -->
            </page>
            <page string="History" name="history">
                <!-- History content -->
            </page>
        </notebook>
    </sheet>

    <!-- Chatter for communication (if applicable) -->
    <div class="oe_chatter">
        <field name="message_follower_ids"/>
        <field name="message_ids"/>
    </div>
</form>
```

### Tab Organization Guidelines

**Maximum Tabs**: 4-6 tabs per form

**Tab Naming**:
- Use clear, concise labels (1-2 words)
- Use icons where appropriate
- Order by importance/usage frequency

**Common Tab Structure**:
1. **Details/Information** - Primary entity data
2. **Financial/Pricing** - Cost-related information
3. **Documents/Attachments** - Files and media
4. **History/Notes** - Audit trail and comments

### Group Layout Best Practices

```xml
<!-- ✅ GOOD: Clear sections, logical grouping -->
<group>
    <group string="Rental Period">
        <field name="pickup_date"/>
        <field name="return_date"/>
        <field name="duration"/>
    </group>
    <group string="Customer Information">
        <field name="customer_id"/>
        <field name="contact_number"/>
    </group>
</group>

<!-- ❌ BAD: No structure, flat fields -->
<group>
    <field name="pickup_date"/>
    <field name="customer_id"/>
    <field name="return_date"/>
    <field name="contact_number"/>
</group>
```

---

## 6. List View Patterns

### Standard List View Structure
```xml
<tree string="Entity List"
      decoration-success="state == 'done'"
      decoration-danger="state == 'failed'">
    <!-- Always visible key fields -->
    <field name="name"/>
    <field name="date"/>

    <!-- Status field (always visible with badge) -->
    <field name="state" widget="badge" optional="show"/>

    <!-- Optional secondary fields -->
    <field name="partner_id" optional="hide"/>
    <field name="amount" optional="show"/>

    <!-- Hidden fields for decoration logic -->
    <field name="is_expired" column_invisible="1"/>
</tree>
```

### Optional Field Guidelines

| Field Priority | Attribute | Usage |
|---------------|-----------|-------|
| **Critical** | `optional="show"` or no attribute | Always visible by default |
| **Important** | `optional="show"` | Visible by default, user can hide |
| **Secondary** | `optional="hide"` | Hidden by default, user can show |
| **System** | `column_invisible="1"` | Never visible, used for logic |

### Decoration Patterns

```xml
<!-- ✅ GOOD: Clear conditions, useful highlighting -->
<tree decoration-success="state == 'completed'"
      decoration-warning="state == 'pending'"
      decoration-danger="is_overdue"
      decoration-muted="state == 'cancelled'">
    <!-- Fields -->
</tree>

<!-- ❌ BAD: Too many decorations, conflicting conditions -->
<tree decoration-success="field1 == 'x' or field2 == 'y' or field3 == 'z'"
      decoration-danger="field1 != 'x' and field2 != 'y'">
    <!-- Confusing logic -->
</tree>
```

---

## 7. Kanban View Patterns

### Standard Kanban Structure
```xml
<kanban default_group_by="state" class="o_kanban_small_column">
    <field name="state"/>
    <field name="priority"/>
    <field name="color"/>
    <templates>
        <t t-name="kanban-box">
            <div t-attf-class="oe_kanban_color_{{kanban_getcolor(record.color.raw_value)}} oe_kanban_card oe_kanban_global_click">
                <div class="o_dropdown_kanban dropdown">
                    <!-- Dropdown menu -->
                </div>
                <div class="oe_kanban_content">
                    <!-- Card header with icon and title -->
                    <div class="o_kanban_record_top">
                        <div class="o_kanban_record_headings">
                            <strong class="o_kanban_record_title">
                                <i class="fa fa-entity-icon"/> <field name="name"/>
                            </strong>
                        </div>
                        <!-- Priority/status badge -->
                        <span t-attf-class="badge badge-pill badge-{{record.state.raw_value}}">
                            <field name="state"/>
                        </span>
                    </div>

                    <!-- Card body with key information -->
                    <div class="o_kanban_record_body">
                        <div class="o_kanban_record_bottom">
                            <div class="oe_kanban_bottom_left">
                                <i class="fa fa-calendar"/> <field name="date"/>
                            </div>
                            <div class="oe_kanban_bottom_right">
                                <field name="user_id" widget="many2one_avatar_user"/>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </t>
    </templates>
</kanban>
```

### Kanban Card Content Guidelines

**Must Include**:
1. Entity name/title (prominent)
2. Status/state badge
3. Key date or deadline
4. Assigned user (if applicable)

**Should Include**:
5. Priority indicator
6. Monetary amount (if financial)
7. Progress indicator (if workflow)

**May Include**:
8. Tags/categories
9. Quick action buttons
10. Thumbnail image

---

## 8. Dashboard & KPI Patterns

### Dashboard Layout Structure
```xml
<form string="Dashboard">
    <sheet>
        <!-- KPI Summary Cards -->
        <div class="row">
            <div class="col-lg-3 col-md-6">
                <div class="card bg-success">
                    <div class="card-body">
                        <h4><field name="available_vehicles_count"/></h4>
                        <p>Available Vehicles</p>
                    </div>
                </div>
            </div>
            <!-- More KPI cards -->
        </div>

        <!-- Charts and Graphs -->
        <group>
            <field name="revenue_chart" widget="graph"/>
            <field name="utilization_gauge" widget="gauge"/>
        </group>

        <!-- Alert/Warning Section -->
        <group string="Alerts">
            <field name="expiring_documents_ids">
                <tree decoration-danger="days_to_expiry &lt; 7">
                    <field name="name"/>
                    <field name="expiry_date"/>
                    <field name="days_to_expiry"/>
                </tree>
            </field>
        </group>
    </sheet>
</form>
```

### KPI Card Classes

| KPI Type | Card Class | Text Class | Icon |
|----------|-----------|------------|------|
| Success Metric | `bg-success` | `text-white` | `fa-check-circle` |
| Revenue/Positive | `bg-primary` | `text-white` | `fa-dollar` |
| Warning Metric | `bg-warning` | `text-dark` | `fa-exclamation-triangle` |
| Alert/Critical | `bg-danger` | `text-white` | `fa-times-circle` |
| Info/Neutral | `bg-info` | `text-white` | `fa-info-circle` |

---

## 9. Alert & Warning Patterns

### Info Box Pattern
```xml
<div class="alert alert-info" role="alert">
    <strong><i class="fa fa-info-circle"/> Information:</strong>
    <ul>
        <li>Point 1</li>
        <li>Point 2</li>
    </ul>
</div>
```

### Warning Box Pattern
```xml
<div class="alert alert-warning" role="alert">
    <strong><i class="fa fa-exclamation-triangle"/> Warning:</strong>
    This action requires attention.
</div>
```

### Danger Box Pattern
```xml
<div class="alert alert-danger" role="alert">
    <strong><i class="fa fa-times-circle"/> Error:</strong>
    Critical issue detected.
</div>
```

### Success Box Pattern
```xml
<div class="alert alert-success" role="alert">
    <strong><i class="fa fa-check-circle"/> Success:</strong>
    Operation completed successfully.
</div>
```

---

## 10. Responsive Design Rules

### Field Visibility Rules

| Screen Size | Critical Fields | Important Fields | Secondary Fields |
|-------------|----------------|------------------|------------------|
| Desktop | Always visible | `optional="show"` | `optional="hide"` |
| Tablet | Always visible | `optional="show"` | Hidden |
| Mobile | Always visible | Hidden | Hidden |

### Responsive Group Layouts
```xml
<!-- Desktop: 2 columns, Tablet: 1 column, Mobile: 1 column -->
<group col="2" class="o_group_responsive">
    <group>
        <field name="field1"/>
    </group>
    <group>
        <field name="field2"/>
    </group>
</group>
```

---

## 11. Accessibility Guidelines

### ARIA Labels
```xml
<!-- Add aria-label for screen readers -->
<button name="action_submit" type="object" aria-label="Submit Form">
    <i class="fa fa-check"/>
</button>
```

### Color Contrast
- Ensure minimum 4.5:1 contrast ratio for text
- Don't rely solely on color to convey information
- Use icons + color together

### Keyboard Navigation
- All interactive elements must be keyboard accessible
- Provide skip links for long forms
- Use proper tab order

---

## 12. Error Message & Validation Patterns

### Validation Error Format
```python
raise ValidationError(
    _('%(entity)s %(name)s %(error_description)s.\n\n'
      'Suggestion: %(suggestion)s') % {
        'entity': 'Driver',
        'name': booking.driver_employee_id.name,
        'error_description': 'is on leave from %s to %s' % (leave.date_from, leave.date_to),
        'suggestion': 'Please select an alternative driver or reschedule the booking.'
    }
)
```

### User-Friendly Error Components
1. **What happened**: Clear description of the issue
2. **Why it happened**: Context or reason (if helpful)
3. **What to do**: Actionable suggestion
4. **Related links**: Links to related records (if applicable)

---

## 13. Implementation Checklist

### For Every New View
- [ ] Status fields use badge widget with proper decorations
- [ ] Optional fields are properly marked (`optional="show/hide"`)
- [ ] Icons used consistently per entity type
- [ ] Responsive layout considered
- [ ] Color scheme follows design system
- [ ] Form has logical tab organization (if applicable)
- [ ] List view has useful decoration highlighting
- [ ] Kanban cards show essential information
- [ ] Error messages are user-friendly
- [ ] ARIA labels for accessibility

### For Dashboard/KPI Views
- [ ] KPI cards use consistent styling
- [ ] Charts have clear labels and legends
- [ ] Alerts prominently displayed
- [ ] Real-time data where possible
- [ ] Mobile-friendly layout

### For Integration Points
- [ ] Cross-module relationships clearly indicated
- [ ] Related record counts shown with stat buttons
- [ ] Integration status visible
- [ ] Error states handled gracefully

---

## 14. Examples & Templates

### Complete Booking Form Example
See: `/car_rental_fleet/views/booking_views.xml` (updated)

### Complete Dashboard Example
See: `/car_rental_fleet/views/dashboard_views.xml` (updated)

### Complete List View Example
See: `/car_rental_fleet/views/vehicle_views.xml` (updated)

---

## 15. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-29 | Initial comprehensive design system documentation |

---

## 16. Maintenance & Updates

This design system should be reviewed and updated:
- When new Odoo version is adopted
- When new modules are added
- When user feedback suggests improvements
- Quarterly review of consistency

---

**End of Design System Documentation**
