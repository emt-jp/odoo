# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

import hashlib
import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# Default dimension weights — see emt-tech/docs/SCORING.md. Override at runtime
# via system parameter `emt_jobhunt.score_weights` (a JSON object).
SCORE_WEIGHTS = {
    'dim_cpp': 18, 'dim_fintech': 16, 'dim_blockchain': 10, 'dim_rust': 8,
    'dim_remote': 12, 'dim_salary': 8, 'dim_experience': 12, 'dim_location': 6,
    'dim_company': 4, 'dim_freelance': 3, 'dim_difficulty': 2, 'dim_urgency': 1,
}
SCORE_WEIGHTS_PARAM = "emt_jobhunt.score_weights"


class JobhuntPosting(models.Model):
    _name = 'jobhunt.posting'
    _description = 'Job Posting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Job Title', required=True, tracking=True)
    source_id = fields.Many2one('jobhunt.source', string='Source')
    dedup_key = fields.Char('Dedup Key', index=True, copy=False,
                            help="sha1(company|title|location|url-host)")
    description_hash = fields.Char('Description Hash',
                                   help="sha256 of normalized description (repost dedup)")

    company_id = fields.Many2one('jobhunt.company', string='Company', tracking=True)
    location = fields.Char('Location')
    work_mode = fields.Selection([
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('onsite', 'On-site'),
        ('unknown', 'Unknown'),
    ], string='Work Mode', default='unknown')
    employment_type = fields.Selection([
        ('full_time', 'Full-time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance'),
        ('unknown', 'Unknown'),
    ], string='Employment Type', default='unknown')

    salary_min = fields.Float('Salary Min')
    salary_max = fields.Float('Salary Max')
    salary_currency = fields.Char('Currency')
    rate_period = fields.Selection([
        ('year', 'Per Year'), ('month', 'Per Month'), ('day', 'Per Day'),
        ('hour', 'Per Hour'), ('unknown', 'Unknown'),
    ], string='Rate Period', default='unknown')

    skills = fields.Char('Skills')
    tech_stack = fields.Char('Tech Stack')
    experience_level = fields.Char('Experience Level')
    visa_restriction = fields.Char('Visa/Location Restriction')
    application_url = fields.Char('Application URL')
    recruiter_id = fields.Many2one('jobhunt.contact', string='Recruiter')
    posted_at = fields.Datetime('Posted At')
    deadline = fields.Datetime('Deadline')
    description = fields.Html('Job Description')

    score_id = fields.Many2one('jobhunt.score', string='Latest Score')
    score_total = fields.Float(related='score_id.total', string='Score', store=True)
    classification = fields.Selection(related='score_id.classification',
                                      string='Classification', store=True)

    state = fields.Selection([
        ('new', 'New'),
        ('scored', 'Scored'),
        ('archived', 'Archived'),
    ], default='new', tracking=True)

    suggested_projects = fields.Text(
        'Suggested Portfolio Projects', compute='_compute_suggested_projects',
        help="Owned GitHub projects whose domain/stack matches this posting")

    application_ids = fields.One2many('jobhunt.application', 'posting_id',
                                      string='Applications')

    _sql_constraints = [
        ('dedup_key_uniq', 'unique(dedup_key)',
         'A posting with this dedup key already exists.'),
    ]

    # --- Dedup helpers -----------------------------------------------------
    @api.model
    def compute_dedup_key(self, company, title, location, url):
        from urllib.parse import urlparse
        host = urlparse(url or '').netloc.lower()
        basis = '|'.join([
            (company or '').strip().lower(),
            (title or '').strip().lower(),
            (location or '').strip().lower(),
            host,
        ])
        return hashlib.sha1(basis.encode('utf-8')).hexdigest()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('dedup_key'):
                company = self.env['jobhunt.company'].browse(
                    vals.get('company_id')).name if vals.get('company_id') else ''
                vals['dedup_key'] = self.compute_dedup_key(
                    company, vals.get('name'), vals.get('location'),
                    vals.get('application_url'))
        return super().create(vals_list)

    # --- Portfolio matching ------------------------------------------------
    @api.depends('name', 'skills', 'tech_stack', 'description')
    def _compute_suggested_projects(self):
        profile = self.env['jobhunt.profile'].get_active()
        github = {}
        if profile and profile.github_json:
            try:
                github = json.loads(profile.github_json)
            except ValueError:
                github = {}
        owned = github.get('owned_projects', []) if isinstance(github, dict) else []
        for posting in self:
            text = posting._haystack()
            matches = []
            for proj in owned:
                if not isinstance(proj, dict):
                    continue
                terms = []
                terms += proj.get('relevance', []) or []
                terms += proj.get('languages', []) or []
                hit = [t for t in terms if str(t).lower() in text]
                if hit:
                    matches.append("%s — matches: %s" % (
                        proj.get('name', '?'), ", ".join(sorted(set(hit)))))
            posting.suggested_projects = "\n".join(matches) or False

    # --- Scoring -----------------------------------------------------------
    def _load_weights(self):
        param = self.env['ir.config_parameter'].sudo().get_param(SCORE_WEIGHTS_PARAM)
        if param:
            try:
                custom = json.loads(param)
                # keep only known dimensions; fall back per-key
                return {k: float(custom.get(k, v)) for k, v in SCORE_WEIGHTS.items()}
            except (ValueError, TypeError):
                _logger.warning("invalid %s, using defaults", SCORE_WEIGHTS_PARAM)
        return dict(SCORE_WEIGHTS)

    def action_score(self):
        """Score each posting against the active master profile.

        Keyword-overlap heuristic per dimension, weighted by configurable
        weights (system param `emt_jobhunt.score_weights`), with honesty caps
        on Rust/blockchain. See docs/SCORING.md.
        """
        profile = self.env['jobhunt.profile'].get_active()
        weights = self._load_weights()
        for posting in self:
            dims = posting._score_dimensions(profile)
            total, is_stretch = posting._weighted_total(dims, weights)
            classification = posting._classify(total)
            score = self.env['jobhunt.score'].create(dict(
                dims,
                posting_id=posting.id,
                profile_version=profile.version if profile else 0,
                total=total,
                is_stretch=is_stretch,
                classification=classification,
                rationale=posting._build_rationale(dims, total, classification, is_stretch),
            ))
            posting.write({'score_id': score.id, 'state': 'scored'})
        return True

    def _haystack(self):
        self.ensure_one()
        parts = [self.name or '', self.skills or '', self.tech_stack or '',
                 self.experience_level or '', self.description or '']
        return ' '.join(parts).lower()

    def _score_dimensions(self, profile):
        """Return a dict of dim_* -> 0..100. Heuristic scaffold."""
        self.ensure_one()
        text = self._haystack()

        def hits(words):
            return sum(1 for w in words if w in text)

        def scaled(words, cap=3):
            return min(100.0, (hits(words) / cap) * 100.0) if words else 0.0

        dims = {
            'dim_cpp': scaled(['c++', 'cpp', 'low latency', 'low-latency', 'hft', 'fix', 'order book']),
            'dim_fintech': scaled(['trading', 'fintech', 'oms', 'matching engine', 'exchange', 'fix']),
            'dim_blockchain': scaled(['crypto', 'blockchain', 'web3', 'defi', 'custody', 'wallet']),
            'dim_rust': scaled(['rust', 'substrate', 'solana', 'anchor']),
            'dim_remote': 100.0 if self.work_mode == 'remote' else (60.0 if self.work_mode == 'hybrid' else (20.0 if self.work_mode == 'onsite' else 50.0)),
            'dim_salary': 50.0,  # neutral when unknown — missing != bad
            'dim_experience': scaled(['senior', 'staff', 'principal', 'lead', 'head', 'architect', 'cto']),
            'dim_location': 100.0 if (self.work_mode == 'remote' and not self.visa_restriction) else 60.0,
            'dim_company': (self.company_id.quality_score or 50.0),
            'dim_freelance': 100.0 if self.employment_type in ('freelance', 'contract') else 40.0,
            'dim_difficulty': 70.0,  # placeholder — fewer hoops = higher
            'dim_urgency': 60.0 if self.deadline else 40.0,
        }
        return dims

    def _weighted_total(self, dims, weights=None):
        weights = weights or SCORE_WEIGHTS
        total_w = sum(weights.values()) or 1.0
        # Honesty cap: if Rust looks like a hard requirement, cap its contribution.
        is_stretch = dims.get('dim_rust', 0) >= 80
        capped = dict(dims)
        if is_stretch:
            capped['dim_rust'] = min(capped['dim_rust'], 40.0)
            capped['dim_blockchain'] = min(capped['dim_blockchain'], 60.0)
        total = sum(capped.get(k, 0.0) * w for k, w in weights.items()) / total_w
        return total, is_stretch

    def _classify(self, total):
        if total >= 80:
            return 'must_apply'
        if total >= 65:
            return 'good_match'
        if total >= 50:
            return 'maybe'
        if total >= 35:
            return 'low_priority'
        return 'not_suitable'

    def _build_rationale(self, dims, total, classification, is_stretch):
        lines = ["%s %.0f" % (k, v) for k, v in sorted(dims.items(), key=lambda x: -x[1])]
        tag = " (stretch: Rust/blockchain capped)" if is_stretch else ""
        return "\n".join(lines) + "\n→ total %.0f → %s%s" % (total, classification, tag)

    def action_archive_posting(self):
        self.write({'state': 'archived'})
