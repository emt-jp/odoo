# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json
import hmac
import hashlib
import logging

_logger = logging.getLogger(__name__)


class PaymentWebhookController(http.Controller):

    # ==================== STRIPE WEBHOOKS ====================

    @http.route('/payment/stripe/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def stripe_webhook(self):
        """Handle Stripe webhook events"""
        payload = request.httprequest.data
        sig_header = request.httprequest.headers.get('Stripe-Signature')

        try:
            import stripe
        except ImportError:
            _logger.error('Stripe library not installed')
            return {'status': 'error', 'message': 'Stripe library not installed'}

        # Get the first company with Stripe configured
        company = request.env['res.company'].sudo().search([
            ('stripe_enabled', '=', True),
            ('stripe_webhook_secret', '!=', False),
        ], limit=1)

        if not company:
            _logger.warning('No company with Stripe webhook secret configured')
            return {'status': 'error', 'message': 'Stripe not configured'}

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, company.stripe_webhook_secret
            )
        except ValueError as e:
            _logger.error('Invalid Stripe payload: %s', e)
            return {'status': 'error', 'message': 'Invalid payload'}
        except stripe.error.SignatureVerificationError as e:
            _logger.error('Invalid Stripe signature: %s', e)
            return {'status': 'error', 'message': 'Invalid signature'}

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._handle_stripe_success(session)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            _logger.info('Stripe PaymentIntent succeeded: %s', payment_intent.get('id'))
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self._handle_stripe_failure(payment_intent)

        return {'status': 'success'}

    def _handle_stripe_success(self, session):
        """Handle successful Stripe checkout session"""
        metadata = session.get('metadata', {})
        transaction_id = metadata.get('transaction_id')

        if not transaction_id:
            _logger.warning('No transaction_id in Stripe session metadata')
            return

        transaction = request.env['payment.transaction.custom'].sudo().search([
            ('id', '=', int(transaction_id)),
            ('provider', '=', 'stripe'),
        ], limit=1)

        if transaction:
            _logger.info('Processing Stripe payment for transaction %s', transaction.name)
            transaction._process_payment_success(webhook_data=session)
        else:
            _logger.warning('Transaction %s not found', transaction_id)

    def _handle_stripe_failure(self, payment_intent):
        """Handle failed Stripe payment"""
        _logger.warning('Stripe payment failed: %s', payment_intent.get('id'))

    @http.route('/payment/success', type='http', auth='public', website=True)
    def payment_success(self, transaction_id=None, **kwargs):
        """Payment success redirect page"""
        if transaction_id:
            transaction = request.env['payment.transaction.custom'].sudo().search([
                ('id', '=', int(transaction_id)),
            ], limit=1)

            if transaction and transaction.state == 'pending':
                # For Stripe, the webhook should handle this, but we can verify
                pass

        return request.render('custom_accounting.payment_success_page', {
            'transaction_id': transaction_id,
        })

    @http.route('/payment/cancel', type='http', auth='public', website=True)
    def payment_cancel(self, transaction_id=None, **kwargs):
        """Payment cancelled redirect page"""
        return request.render('custom_accounting.payment_cancel_page', {
            'transaction_id': transaction_id,
        })

    # ==================== PAYPAY WEBHOOKS ====================

    @http.route('/payment/paypay/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def paypay_webhook(self):
        """Handle PayPay webhook events"""
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            _logger.error('Invalid PayPay webhook payload')
            return {'status': 'error', 'message': 'Invalid JSON'}

        notification_type = data.get('notification_type')
        merchant_payment_id = data.get('merchant_payment_id')

        _logger.info('PayPay webhook received: %s for %s', notification_type, merchant_payment_id)

        if notification_type == 'transaction.completed':
            self._handle_paypay_success(data)
        elif notification_type == 'transaction.failed':
            self._handle_paypay_failure(data)

        return {'status': 'success'}

    def _handle_paypay_success(self, data):
        """Handle successful PayPay payment"""
        merchant_payment_id = data.get('merchant_payment_id')

        transaction = request.env['payment.transaction.custom'].sudo().search([
            ('provider_reference', '=', merchant_payment_id),
            ('provider', '=', 'paypay'),
        ], limit=1)

        if transaction:
            _logger.info('Processing PayPay payment for transaction %s', transaction.name)
            transaction._process_payment_success(webhook_data=data)
        else:
            _logger.warning('PayPay transaction %s not found', merchant_payment_id)

    def _handle_paypay_failure(self, data):
        """Handle failed PayPay payment"""
        merchant_payment_id = data.get('merchant_payment_id')

        transaction = request.env['payment.transaction.custom'].sudo().search([
            ('provider_reference', '=', merchant_payment_id),
            ('provider', '=', 'paypay'),
        ], limit=1)

        if transaction:
            transaction.write({
                'state': 'error',
                'error_message': data.get('result_info', {}).get('message', 'Payment failed'),
                'webhook_data': json.dumps(data),
            })

    @http.route('/payment/paypay/callback', type='http', auth='public', website=True)
    def paypay_callback(self, transaction_id=None, **kwargs):
        """PayPay redirect callback"""
        # PayPay redirects here after payment
        # The actual payment confirmation comes via webhook
        return request.redirect('/payment/success?transaction_id=%s' % transaction_id)

    # ==================== AIRPAY WEBHOOKS ====================

    @http.route('/payment/airpay/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def airpay_webhook(self):
        """Handle AirPay webhook events"""
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            _logger.error('Invalid AirPay webhook payload')
            return {'status': 'error', 'message': 'Invalid JSON'}

        event_type = data.get('event_type')
        payment_id = data.get('payment_id')

        _logger.info('AirPay webhook received: %s for %s', event_type, payment_id)

        if event_type == 'payment.completed':
            self._handle_airpay_success(data)
        elif event_type == 'payment.failed':
            self._handle_airpay_failure(data)

        return {'status': 'success'}

    def _handle_airpay_success(self, data):
        """Handle successful AirPay payment"""
        payment_ref = data.get('merchant_reference')

        transaction = request.env['payment.transaction.custom'].sudo().search([
            ('provider_reference', '=', payment_ref),
            ('provider', '=', 'airpay'),
        ], limit=1)

        if transaction:
            _logger.info('Processing AirPay payment for transaction %s', transaction.name)
            transaction._process_payment_success(webhook_data=data)
        else:
            _logger.warning('AirPay transaction %s not found', payment_ref)

    def _handle_airpay_failure(self, data):
        """Handle failed AirPay payment"""
        payment_ref = data.get('merchant_reference')

        transaction = request.env['payment.transaction.custom'].sudo().search([
            ('provider_reference', '=', payment_ref),
            ('provider', '=', 'airpay'),
        ], limit=1)

        if transaction:
            transaction.write({
                'state': 'error',
                'error_message': data.get('error_message', 'Payment failed'),
                'webhook_data': json.dumps(data),
            })

    # ==================== MANUAL CONFIRMATION ====================

    @http.route('/payment/confirm/<int:transaction_id>', type='http', auth='user', website=True)
    def manual_confirm(self, transaction_id, **kwargs):
        """Manual payment confirmation (for admin)"""
        transaction = request.env['payment.transaction.custom'].browse(transaction_id)

        if not transaction.exists():
            return request.redirect('/web')

        if request.env.user.has_group('account.group_account_manager'):
            transaction.action_confirm_payment()
            return request.redirect(f'/web#id={transaction.invoice_id.id}&model=account.move&view_type=form')

        return request.redirect('/web')
