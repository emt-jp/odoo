# emt_jobhunt — Personal Job-Hunt ATS (Odoo 19 addon)

Spine for the emt-tech job-hunting platform. Tracks scraped job postings, scores
them against a master profile, manages applications through a kanban pipeline, and
stores generated resumes/cover letters — **isolated from company ERP data**.

> Candidate-applying-to-jobs direction (NOT hiring). Deliberately does not use
> `hr_recruitment`, `crm.lead`, or `res.partner`. Design lives in `~/ws/emt-tech/docs/`.

## Models
| Model | Purpose |
|---|---|
| `jobhunt.source` | scrape provenance (url, method, confidence, raw payload) |
| `jobhunt.posting` | normalized job + dedup key + scoring + state |
| `jobhunt.score` | 12-dimension opportunity score + classification + rationale |
| `jobhunt.application` | pipeline (kanban stages) + resume/cover attachments + follow-ups |
| `jobhunt.stage` | configurable pipeline stages (seeded) |
| `jobhunt.company` / `jobhunt.contact` | isolated recruiter/company CRM |
| `jobhunt.profile` | mirror of master-profile.yaml (scoring + generator read it) |

## Security / isolation
- Group **Job Hunt User** (`group_jobhunt_user`); all models granted only to it
  (`ir.model.access.csv`) + `ir.rule` belt-and-suspenders.
- Root menu restricted to the group → invisible to other company users.
- ⚠️ The Odoo **superuser/admin bypasses** access rules. Isolation holds against
  normal company users. **Test:** log in as a non-jobhunt company user and confirm
  no `jobhunt.*` menu/record is visible.

## Install (dev)
```bash
cd ~/ws/odoo && docker-compose up -d
# Apps → Update Apps List → install "EMT Job Hunt"
# Then assign your user to Settings → Users → group "Job Hunt User".
```

## Status: scaffold (v0.1.0)
- ✅ Models, security, stages seed, kanban/list/form/search views, menus.
- ✅ Scoring `action_score` is a working keyword heuristic — replace with the full
  weighted model in `emt-tech/docs/SCORING.md`.
- ⬜ External workers (scanner push, generator) wired via Odoo API key (`jobhunt-bot`).
- ⬜ Load `master-profile.yaml` into `jobhunt.profile` (install hook or API).
