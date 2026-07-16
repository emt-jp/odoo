# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform. See emt-tech/docs for design.

{
    'name': 'EMT Job Hunt',
    'version': '0.1.0',
    'category': 'Productivity',
    'summary': 'Personal job-hunting ATS — postings, scoring, applications, outreach',
    'description': """
        EMT Job Hunt
        ============

        Personal applicant-tracking spine for the emt-tech job-hunting platform.
        Tracks scraped job postings, scores them against a master profile,
        manages applications through a kanban pipeline, and stores generated
        resumes/cover letters — all isolated from company ERP data.

        NOTE: This is the *candidate-applying-to-jobs* direction, NOT hiring.
        It deliberately does NOT use hr_recruitment, crm.lead, or res.partner —
        dedicated models keep personal/PII data isolated. Access is restricted to
        the 'Job Hunt User' group via ir.model.access + ir.rule.

        External Python workers (scanner, generator) feed this addon over the
        Odoo External API.
    """,
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        'security/jobhunt_security.xml',
        'security/ir.model.access.csv',
        'data/jobhunt_stage_data.xml',
        'data/jobhunt_config_data.xml',
        'data/jobhunt_cron.xml',
        'views/jobhunt_posting_views.xml',
        'views/jobhunt_application_views.xml',
        'views/jobhunt_interview_views.xml',
        'views/jobhunt_crm_views.xml',
        'views/jobhunt_source_score_views.xml',
        'views/jobhunt_profile_views.xml',
        'views/jobhunt_menus.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Prasanta Sahoo',
}
