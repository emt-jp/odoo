# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

import json
import logging
import urllib.request
import urllib.error
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# System parameters: generator webhook base URL + optional shared secret.
GENERATOR_URL_PARAM = "emt_jobhunt.generator_url"
GENERATOR_SECRET_PARAM = "emt_jobhunt.generator_secret"

# Default follow-up cadence (days after applying) — overridable via system param.
FOLLOWUP_DAYS_PARAM = "emt_jobhunt.followup_days"
DEFAULT_FOLLOWUP_DAYS = 5


class JobhuntApplication(models.Model):
    _name = 'jobhunt.application'
    _description = 'Job Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    posting_id = fields.Many2one('jobhunt.posting', string='Posting',
                                 required=True, ondelete='restrict', tracking=True)
    company_id = fields.Many2one(related='posting_id.company_id', store=True,
                                 string='Company')
    stage_id = fields.Many2one('jobhunt.stage', string='Stage', tracking=True,
                               group_expand='_read_group_stage_ids',
                               default=lambda self: self.env['jobhunt.stage'].search([], limit=1))

    # Generated documents — stored as attachments (traceable to the posting).
    resume_attachment_id = fields.Many2one('ir.attachment', string='Resume',
                                            domain="[('res_model','=','jobhunt.application')]")
    cover_attachment_id = fields.Many2one('ir.attachment', string='Cover Letter',
                                           domain="[('res_model','=','jobhunt.application')]")
    resume_archetype = fields.Char('Resume Archetype')
    lead_client_window = fields.Char(
        'Lead-client note',
        help="Resume timeline: which client leads each overlapping window "
             "(advised at generation time — one client per window).")

    applied_at = fields.Datetime('Applied At', tracking=True)
    contact_id = fields.Many2one('jobhunt.contact', string='Contact')
    followup_at = fields.Date('Next Follow-up')
    notes = fields.Html('Notes')
    interview_feedback = fields.Text('Interview Feedback')
    outcome = fields.Char('Outcome')

    interview_ids = fields.One2many('jobhunt.interview', 'application_id',
                                    string='Interviews')
    interview_count = fields.Integer('Interviews', compute='_compute_interview_count')

    score_total = fields.Float(related='posting_id.score_total', string='Score', store=True)
    classification = fields.Selection(related='posting_id.classification',
                                      string='Classification', store=True)

    def _compute_interview_count(self):
        for rec in self:
            rec.interview_count = len(rec.interview_ids)

    @api.depends('posting_id', 'posting_id.company_id')
    def _compute_name(self):
        for rec in self:
            title = rec.posting_id.name or 'Application'
            company = rec.posting_id.company_id.name or ''
            rec.name = ("%s — %s" % (title, company)).strip(' —')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        # Show all stages as kanban columns even when empty.
        return self.env['jobhunt.stage'].search([])

    # --- Follow-up cadence -------------------------------------------------
    def _followup_days(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            FOLLOWUP_DAYS_PARAM)
        try:
            return int(param) if param else DEFAULT_FOLLOWUP_DAYS
        except (TypeError, ValueError):
            return DEFAULT_FOLLOWUP_DAYS

    def _maybe_set_applied(self, vals):
        """When an application enters the 'Applied' stage, stamp applied_at and
        schedule the next follow-up date."""
        applied_stage = self.env.ref('emt_jobhunt.stage_applied',
                                     raise_if_not_found=False)
        if not applied_stage or vals.get('stage_id') != applied_stage.id:
            return vals
        days = self._followup_days()
        vals = dict(vals)
        vals.setdefault('applied_at', fields.Datetime.now())
        vals.setdefault('followup_at',
                        fields.Date.context_today(self) + timedelta(days=days))
        return vals

    def write(self, vals):
        if 'stage_id' in vals:
            vals = self._maybe_set_applied(vals)
        return super().write(vals)

    @api.model
    def _cron_followups(self):
        """Daily: for applications whose follow-up date is due and that are still
        waiting, schedule a To-Do activity (a reminder — NOT an auto-send) and
        move them to the 'Follow-up Needed' stage."""
        today = fields.Date.context_today(self)
        followup_stage = self.env.ref('emt_jobhunt.stage_followup',
                                      raise_if_not_found=False)
        applied_stage = self.env.ref('emt_jobhunt.stage_applied',
                                     raise_if_not_found=False)
        recruiter_replied = self.env.ref('emt_jobhunt.stage_recruiter_replied',
                                         raise_if_not_found=False)
        waiting_stage_ids = [s.id for s in (applied_stage, recruiter_replied) if s]
        due = self.search([
            ('followup_at', '<=', today),
            ('stage_id', 'in', waiting_stage_ids),
        ])
        todo = self.env.ref('mail.mail_activity_data_todo',
                            raise_if_not_found=False)
        for app in due:
            # Avoid piling up duplicate reminders.
            existing = app.activity_ids.filtered(
                lambda a: a.activity_type_id == (todo and todo) and
                a.date_deadline == today)
            if not existing:
                app.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=today,
                    summary=_('Follow up on application'),
                    note=_('Follow-up due for %s. Draft a polite nudge to the '
                           'recruiter/contact (no auto-send).') % app.name,
                )
            if followup_stage:
                app.stage_id = followup_stage.id
        if due:
            _logger.info("jobhunt: scheduled %s follow-up reminders", len(due))
        return True

    def action_generate_resume(self):
        """Call the external generator worker to render & attach a resume.

        The worker reads the master profile + posting, renders the resume
        (honoring one-client-per-window), and attaches the result back here.
        Returns 409 with `needs_lead_choice` when overlapping engagements have
        no lead client set — surfaced to the user as an actionable error.
        """
        self.ensure_one()
        return self._call_generator(doc_type="resume")

    def action_generate_cover_letter(self):
        self.ensure_one()
        return self._call_generator(doc_type="cover_letter")

    def _call_generator(self, doc_type="resume"):
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            GENERATOR_URL_PARAM)
        if not base_url:
            raise UserError(_(
                "Generator URL is not configured. Set the system parameter "
                "'%s' to the generator webhook (e.g. http://generator:5001).")
                % GENERATOR_URL_PARAM)

        payload = json.dumps({
            "application_id": self.id,
            "archetype": self.resume_archetype or False,
            "doc_type": doc_type,
            "fmt": "docx",
            "include_pii": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        secret = self.env["ir.config_parameter"].sudo().get_param(
            GENERATOR_SECRET_PARAM)
        if secret:
            headers["X-Generator-Secret"] = secret
        req = urllib.request.Request(
            base_url.rstrip("/") + "/generate", data=payload,
            headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            try:
                data = json.loads(body)
            except ValueError:
                data = {}
            if e.code == 409 and data.get("needs_lead_choice"):
                raise UserError(_(
                    "Overlapping engagements need a lead client before the "
                    "resume can be built. Set 'Lead-client note' on this "
                    "application (format: KeepCompany>DropCompany, "
                    "comma-separated).\n\n%s") % data["needs_lead_choice"])
            raise UserError(_("Generator error (%s): %s") % (e.code, body[:300]))
        except urllib.error.URLError as e:
            raise UserError(_("Could not reach the generator: %s") % e)

        self.message_post(body=_("Generated %s — attachment %s (archetype: %s)") % (
            doc_type, result.get("attachment_id"), result.get("archetype")))
        return True
