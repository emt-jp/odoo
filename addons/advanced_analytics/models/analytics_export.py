# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import io
import csv
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class AnalyticsExport(models.Model):
    _name = 'analytics.export'
    _description = 'Analytics Export'

    name = fields.Char('Export Name', required=True)
    export_type = fields.Selection([
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ], string='Export Type', required=True, default='csv')

    # Alias for view compatibility
    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ], string='Export Format', default='csv')

    export_date = fields.Datetime('Export Date', default=fields.Datetime.now)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='draft')

    data = fields.Text('Export Data')
    file_data = fields.Binary('File Data')
    file_name = fields.Char('File Name')
    file_size = fields.Integer('File Size')
    
    # Export configuration
    model_name = fields.Char('Model Name', required=True)
    field_names = fields.Text('Field Names', help='Comma-separated list of fields to export')
    domain = fields.Text('Domain', help='Domain filter for export data')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.model
    def export_data(self, model_name, field_names, domain=None, export_type='csv'):
        """Export data to specified format"""
        if not self._is_enterprise_available():
            raise UserError(_("Data export requires the Enterprise edition."))
        
        model = self.env[model_name]
        records = model.search(domain or [])
        
        if not records:
            raise UserError(_("No data found to export."))
        
        field_list = [f.strip() for f in field_names.split(',')] if field_names else []
        
        if export_type == 'csv':
            return self._export_to_csv(records, field_list)
        elif export_type == 'excel':
            return self._export_to_excel(records, field_list)
        elif export_type == 'pdf':
            return self._export_to_pdf(records, field_list)
        elif export_type == 'json':
            return self._export_to_json(records, field_list)
        
        raise UserError(_("Unsupported export type: %s") % export_type)
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _export_to_csv(self, records, field_names):
        """Export data to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        if field_names:
            writer.writerow(field_names)
        else:
            # Get all field names from first record
            field_names = list(records[0]._fields.keys())
            writer.writerow(field_names)
        
        # Write data
        for record in records:
            row = []
            for field_name in field_names:
                if hasattr(record, field_name):
                    value = getattr(record, field_name)
                    if hasattr(value, 'name'):
                        row.append(str(value.name))
                    else:
                        row.append(str(value))
                else:
                    row.append('')
            writer.writerow(row)
        
        csv_data = output.getvalue()
        output.close()
        
        # Create export record
        export = self.create({
            'name': f"Export_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'export_type': 'csv',
            'data': csv_data,
            'file_data': base64.b64encode(csv_data.encode('utf-8')),
            'file_name': f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            'file_size': len(csv_data),
            'model_name': records._name,
            'field_names': ','.join(field_names),
            'domain': str(domain) if domain else '',
        })
        
        return {
            'export_id': export.id,
            'file_name': export.file_name,
            'file_data': export.file_data,
            'file_size': export.file_size,
        }
    
    def _export_to_excel(self, records, field_names):
        """Export data to Excel format"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Excel export requires xlsxwriter library. Please install it first."))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Export')
        
        # Write header
        if field_names:
            for col, field_name in enumerate(field_names):
                worksheet.write(0, col, field_name)
        else:
            field_names = list(records[0]._fields.keys())
            for col, field_name in enumerate(field_names):
                worksheet.write(0, col, field_name)
        
        # Write data
        for row, record in enumerate(records, 1):
            for col, field_name in enumerate(field_names):
                if hasattr(record, field_name):
                    value = getattr(record, field_name)
                    if hasattr(value, 'name'):
                        worksheet.write(row, col, str(value.name))
                    else:
                        worksheet.write(row, col, str(value))
                else:
                    worksheet.write(row, col, '')
        
        workbook.close()
        excel_data = output.getvalue()
        output.close()
        
        # Create export record
        export = self.create({
            'name': f"Export_{records._name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'export_type': 'excel',
            'file_data': base64.b64encode(excel_data),
            'file_name': f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            'file_size': len(excel_data),
            'model_name': records._name,
            'field_names': ','.join(field_names),
        })
        
        return {
            'export_id': export.id,
            'file_name': export.file_name,
            'file_data': export.file_data,
            'file_size': export.file_size,
        }
    
    def _export_to_pdf(self, records, field_names):
        """Export data to PDF format"""
        # This is a simplified PDF export
        # In a real implementation, you would use a proper PDF library like reportlab
        
        pdf_content = f"""
        <html>
        <head>
            <title>Export Report</title>
        </head>
        <body>
            <h1>Export Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total records: {len(records)}</p>
            <table border="1">
                <tr>
        """
        
        # Add headers
        if field_names:
            for field_name in field_names:
                pdf_content += f"<th>{field_name}</th>"
        else:
            field_names = list(records[0]._fields.keys())
            for field_name in field_names:
                pdf_content += f"<th>{field_name}</th>"
        
        pdf_content += "</tr>"
        
        # Add data rows
        for record in records:
            pdf_content += "<tr>"
            for field_name in field_names:
                if hasattr(record, field_name):
                    value = getattr(record, field_name)
                    if hasattr(value, 'name'):
                        pdf_content += f"<td>{value.name}</td>"
                    else:
                        pdf_content += f"<td>{value}</td>"
                else:
                    pdf_content += "<td></td>"
            pdf_content += "</tr>"
        
        pdf_content += """
                </table>
            </body>
        </html>
        """
        
        # Create export record
        export = self.create({
            'name': f"Export_{records._name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'export_type': 'pdf',
            'data': pdf_content,
            'file_data': base64.b64encode(pdf_content.encode('utf-8')),
            'file_name': f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            'file_size': len(pdf_content),
            'model_name': records._name,
            'field_names': ','.join(field_names),
        })
        
        return {
            'export_id': export.id,
            'file_name': export.file_name,
            'file_data': export.file_data,
            'file_size': export.file_size,
        }
    
    def _export_to_json(self, records, field_names):
        """Export data to JSON format"""
        data = []
        
        for record in records:
            record_data = {'id': record.id}
            for field_name in field_names:
                if hasattr(record, field_name):
                    value = getattr(record, field_name)
                    if hasattr(value, 'name'):
                        record_data[field_name] = value.name
                    else:
                        record_data[field_name] = str(value)
            data.append(record_data)
        
        json_data = json.dumps(data, indent=2, default=str)
        
        # Create export record
        export = self.create({
            'name': f"Export_{records._name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'export_type': 'json',
            'data': json_data,
            'file_data': base64.b64encode(json_data.encode('utf-8')),
            'file_name': f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            'file_size': len(json_data),
            'model_name': records._name,
            'field_names': ','.join(field_names),
        })
        
        return {
            'export_id': export.id,
            'file_name': export.file_name,
            'file_data': export.file_data,
            'file_size': export.file_size,
        }
    
    def download_file(self):
        """Download the exported file"""
        if not self.file_data:
            raise UserError(_("No file data available for download."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=analytics.export&id={self.id}&field=file_data&filename_field=file_name&download=true',
            'target': 'new',
        }




