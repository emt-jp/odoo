# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields, api, _

# Archetype-aware prep prompts. Kept Odoo-side (no external worker needed).
PREP_BY_TYPE = {
    'technical': [
        "Re-derive core data structures / algorithms from scratch on a whiteboard.",
        "Be ready to reason about time/space complexity out loud.",
        "Have 2-3 'hardest bug I debugged' stories ready (FIX/latency/concurrency).",
    ],
    'system_design': [
        "Sketch a low-latency order-entry / matching path end to end.",
        "Discuss back-pressure, partitioning, failover, and exactly-once concerns.",
        "Quantify: throughput target, p99 latency budget, capacity headroom.",
    ],
    'behavioral': [
        "Prepare STAR stories: zero-incident JPX go-live, MiFID II delivery, leading offshore teams.",
        "Have a 'disagreed with a senior stakeholder' and a 'project that failed' story.",
    ],
    'hr_screen': [
        "Tighten the 90-second intro: 25y, Tokyo FinTech, trading + crypto.",
        "Know your salary range and notice period; confirm remote/visa expectations.",
    ],
    'take_home': [
        "Clarify scope + time budget before starting; document assumptions.",
        "Ship tests + a short README explaining trade-offs.",
    ],
    'onsite': [
        "Map the loop: who, what each round tests, lunch/culture signals.",
        "Prepare 3 thoughtful questions per interviewer.",
    ],
}

ARCHETYPE_TOPICS = {
    'cpp_low_latency_engineer': "C++ memory model, lock-free queues, cache effects, FIX/OUCH, FPGA basics.",
    'crypto_exchange_engineer': "Order book mechanics, matching engine, custody/wallets, settlement, market data.",
    'fintech_backend_engineer': "Trading lifecycle, idempotency, reconciliation, Kafka, exactly-once.",
    'trading_systems_architect': "Org design, build-vs-buy, latency budgets, regulatory (MiFID/JPX).",
    'devops_platform_engineer': "K8s, Terraform, CI/CD, observability, incident response.",
    'rust_blockchain_engineer': "Rust ownership/borrowing, async, Substrate/Solana basics — frame as actively learning.",
}


class JobhuntInterview(models.Model):
    _name = 'jobhunt.interview'
    _description = 'Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_at desc, round_no'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    application_id = fields.Many2one('jobhunt.application', string='Application',
                                     required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='application_id.company_id', store=True)
    round_no = fields.Integer('Round', default=1)
    interview_type = fields.Selection([
        ('hr_screen', 'HR Screen'),
        ('technical', 'Technical'),
        ('system_design', 'System Design'),
        ('behavioral', 'Behavioral'),
        ('take_home', 'Take-home'),
        ('onsite', 'Onsite Loop'),
        ('other', 'Other'),
    ], string='Type', default='technical', required=True)
    scheduled_at = fields.Datetime('Scheduled At', tracking=True)
    interviewer = fields.Char('Interviewer(s)')
    prep_notes = fields.Html('Prep Notes')
    questions = fields.Text('Anticipated Questions')
    feedback = fields.Text('Post-interview Feedback')
    result = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('mixed', 'Mixed'),
        ('failed', 'Failed'),
    ], default='pending', tracking=True)

    @api.depends('application_id', 'round_no', 'interview_type')
    def _compute_name(self):
        for rec in self:
            label = dict(self._fields['interview_type'].selection).get(
                rec.interview_type, '')
            rec.name = _("Round %s · %s") % (rec.round_no or 1, label)

    def action_generate_prep(self):
        """Generate an archetype-aware prep checklist + question seeds."""
        for rec in self:
            archetype = rec.application_id.resume_archetype or 'cpp_low_latency_engineer'
            checklist = PREP_BY_TYPE.get(rec.interview_type, [])
            topics = ARCHETYPE_TOPICS.get(archetype, "")
            company = rec.company_id.name or "the company"
            notes = ["<p><b>Prep checklist:</b></p><ul>"]
            notes += [f"<li>{c}</li>" for c in checklist]
            notes.append("</ul>")
            notes.append(f"<p><b>Focus topics ({archetype}):</b> {topics}</p>")
            notes.append(f"<p><b>Company research:</b> recent news on {company}, "
                         "their tech stack, the team you'd join, and why this role.</p>")
            rec.prep_notes = "".join(notes)
            rec.questions = (
                "- Walk me through your most latency-sensitive system.\n"
                "- How would you design/scale <their core system>?\n"
                "- Tell me about leading the JPX zero-incident go-live.\n"
                "- Where are you with Rust / blockchain? (honest: actively learning)\n"
                "- Your questions for them (team, roadmap, on-call, remote norms)."
            )
            rec.message_post(body=_("Prep generated for %s") % rec.name)
        return True
