# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tdc_password_hash = fields.Char(
        string='TDC Password Hash',
        help='Bcrypt password hash for TDC web authentication',
        groups='base.group_system',
    )
    email_verified = fields.Boolean(
        string='Email Verified',
        default=False,
        help='Whether the partner has verified their email address via TDC',
    )
    is_rental_customer = fields.Boolean(
        string='Is Rental Customer',
        default=False,
        help='Whether this partner is a TDC rental customer',
    )
    bio = fields.Text(
        string='Bio',
        help='Public description of the supplier/company',
    )

    # Affiliate program fields
    is_affiliate = fields.Boolean(
        string='Is Affiliate',
        default=False,
        help='Whether this partner is a TDC affiliate',
    )
    affiliate_code = fields.Char(
        string='Affiliate Code',
        help='Unique affiliate referral code',
        index=True,
    )
    affiliate_commission_rate = fields.Float(
        string='Commission Rate',
        default=0.10,
        help='Affiliate commission rate (0.10 = 10%)',
    )
    affiliate_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
    ], string='Affiliate Status', default='pending',
        help='Current affiliate program status',
    )
    affiliate_payment_method = fields.Char(
        string='Affiliate Payment Method',
        help='Preferred payout method (bank_transfer, paypal, etc.)',
    )
    affiliate_payment_details = fields.Text(
        string='Affiliate Payment Details',
        help='Payment details for affiliate payouts',
    )

    # Marketplace vendor fields (Stripe Connect payouts) — emt-jp/tdc Phase 1.
    # A vendor is a supplier partner who lists vehicles (see submitted_by_vendor_id
    # on fleet.vehicle). These fields let the platform take a commission and pay
    # the vendor their share via a Stripe Connect (Express) account.
    stripe_connect_account_id = fields.Char(
        string='Stripe Connect Account',
        help='The vendor\'s Stripe Connect (Express) account id (acct_...), '
             'used as the destination for split payouts.',
        copy=False,
        groups='base.group_system',
    )
    connect_charges_enabled = fields.Boolean(
        string='Connect Charges Enabled',
        default=False,
        help='Synced from Stripe account.updated — the vendor can receive '
             'destination charges. Gate a vendor\'s listings until this is true.',
    )
    connect_payouts_enabled = fields.Boolean(
        string='Connect Payouts Enabled',
        default=False,
        help='Synced from Stripe account.updated — Stripe can pay out to the '
             'vendor\'s bank.',
    )
    platform_commission_rate = fields.Float(
        string='Platform Commission Rate',
        default=0.15,
        help='Platform take on this vendor\'s bookings (0.15 = 15%). '
             'Overridable per vehicle via commission_rate.',
    )

    # Renter documents (emt-jp/tdc#382). Captured by staff at the counter (or
    # from the documents the renter sends ahead) and used by the api-adapter
    # to check eligibility and pre-fill the printed rental agreement. Licence
    # number, country, expiry and date of birth already live on the partner
    # (driving_license_* / birthdate, car_rental_website); these are the rest.
    # Internal users only: none of this is exposed to the customer portal.
    tdc_passport_number = fields.Char(
        string='Passport Number', copy=False, groups='base.group_user')
    tdc_passport_expiry = fields.Date(
        string='Passport Expiry', copy=False, groups='base.group_user')
    tdc_nationality_id = fields.Many2one(
        'res.country', string='Nationality', copy=False, groups='base.group_user')
    tdc_license_issuer = fields.Char(
        string='Licence Issuing Authority', copy=False, groups='base.group_user',
        help='e.g. "Préfecture de l\'Orne" or "DVLA".')
    tdc_license_categories = fields.Char(
        string='Licence Categories', copy=False, groups='base.group_user',
        help='As printed on the licence, e.g. "AM, B1, B".')
    tdc_license_first_issued = fields.Date(
        string='Licence Category B First Issued', copy=False, groups='base.group_user',
        help='Date the category being rented (usually B) was first obtained — '
             'on EU licences the date beside the category, not the card issue '
             'date. The "licence held" eligibility check uses this.')
    tdc_permit_type = fields.Selection([
        ('none', 'None'),
        ('japanese', 'Japanese licence'),
        ('idp', 'International Driving Permit (Geneva 1949)'),
        ('jaf', 'JAF Japanese translation'),
    ], string='Driving Permit for Japan', copy=False, groups='base.group_user')
    tdc_permit_number = fields.Char(
        string='Permit / Translation Number', copy=False, groups='base.group_user')
    tdc_permit_issued = fields.Date(
        string='Permit Issued', copy=False, groups='base.group_user')
    tdc_permit_expiry = fields.Date(
        string='Permit Expiry', copy=False, groups='base.group_user')
    tdc_documents_verified_by = fields.Many2one(
        'res.users', string='Documents Checked By', copy=False, groups='base.group_user')
    tdc_documents_verified_at = fields.Datetime(
        string='Documents Checked At', copy=False, groups='base.group_user')
