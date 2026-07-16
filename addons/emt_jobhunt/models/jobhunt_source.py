# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields


class JobhuntSource(models.Model):
    _name = 'jobhunt.source'
    _description = 'Job Posting Source (scrape provenance)'
    _order = 'scraped_at desc'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    adapter_id = fields.Char('Adapter', required=True,
                             help="e.g. remoteok, web3career, github, rss, manual")
    source_url = fields.Char('Source URL')
    scrape_method = fields.Selection([
        ('api', 'API'),
        ('html', 'HTML'),
        ('rss', 'RSS'),
        ('email', 'Email'),
        ('manual', 'Manual'),
    ], string='Scrape Method', default='manual', required=True)
    scraped_at = fields.Datetime('Scraped At', default=fields.Datetime.now)
    confidence = fields.Float('Confidence', help="Extraction confidence 0.0–1.0")
    raw_payload = fields.Text('Raw Payload', help="Original blob for re-parse/audit")
    posting_ids = fields.One2many('jobhunt.posting', 'source_id', string='Postings')

    def _compute_name(self):
        for rec in self:
            rec.name = "%s · %s" % (rec.adapter_id or '?', rec.scrape_method or '')
