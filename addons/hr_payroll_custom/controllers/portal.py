# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class PayslipPortal(CustomerPortal):
    
    @http.route(['/my/payslips'], type='http', auth="user", website=True)
    def portal_my_payslips(self, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not employee:
            return request.render('portal.portal_my_home', {})
        
        payslips = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
        ], order='date_from desc')
        
        return request.render('hr_payroll_custom.portal_my_payslips', {
            'payslips': payslips,
        })
    
    @http.route(['/my/payslips/<int:payslip_id>/pdf'], type='http', auth="user")
    def portal_payslip_pdf(self, payslip_id, **kw):
        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        
        if not payslip or payslip.employee_id != employee:
            return request.not_found()
        
        pdf = request.env.ref('hr_payroll_custom.action_report_payslip').sudo()._render_qweb_pdf([payslip.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Payslip_{payslip.number}.pdf"')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
