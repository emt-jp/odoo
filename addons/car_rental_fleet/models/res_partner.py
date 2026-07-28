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
