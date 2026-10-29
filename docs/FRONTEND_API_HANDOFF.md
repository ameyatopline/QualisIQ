# SAP Fiori-style frontend API handoff

Use `@ui5/webcomponents-react` and React Router. Authenticate using `/api/v1/auth/login` and store tokens safely in a demo-only client; production requires OIDC with secure session design. Show permanent `SYNTHETIC / NON-GMP` banner when using demonstration tenant.

| Fiori application | Primary API | Drill-down |
|---|---|---|
| Quality Control Tower (Overview) | GET `/api/v1/analytics/overview` | Click alert numbers → quality events |
| Site Directory | GET `/api/v1/master/sites` | Plant/region worklists |
| Material Directory | GET `/api/v1/master/materials` | Versioned specs: next API milestone |
| Inspection Lots | GET `/api/v1/lab/inspection-lots` | Sample and characteristic Object Page: next milestone |
| Laboratory Results (List Report) | GET `/api/v1/lab/results` | Result → specification/version → quality event |
| Laboratory Data Intake | POST `/api/v1/lab/results` or `/bulk` | Distinct source id and status |
| Exceptions and Notifications | GET `/api/v1/quality/events` | GET `/{id}` Object Page |
| Investigation Editor | PATCH `/api/v1/quality/events/{id}/investigation` | Source record/evidence and controlled workflow |
| Investigation Workflow | POST `/api/v1/quality/events/{id}/transition` | Server-authorized state machine |
| Evidence | POST `/api/v1/quality/events/{id}/evidence` | Metadata references; storage viewer next |
| CAPA | POST `/api/v1/quality/events/{id}/capa`; POST `/api/v1/quality/capa/{id}/update` | Assigned actions / effectiveness review |
| QualisIQ Assistant | GET `/api/v1/quality/events/{id}/ai-brief` | Source-linked demo checklist (no live LLM) |
| Audit Console | GET `/api/v1/audit/events`, `/audit/verify` | Auditor/QA Head/Admin only |
| Integration Monitor | GET `/api/v1/integrations/outbox` | Pending messages; worker needed |

## Screen structure

- Launchpad → **Quality Engineer Overview** (multi-level KPI, exceptions by site/status, overdue CAPA)
- Sidebar → Master Data / QC Lab / Quality Events / CAPA / Documents / Analytics / Connect / Governance
- Quality event Object Page tabs: Overview / Source Laboratory Result / Phase I / Phase II or OOT Review / QualisIQ / Evidence / CAPA / QA Review / Audit
- Event header: severity, type, site, material, batch, source record, status, assigned actor and version. Buttons only for server-permitted transitions; always handle 403/409.
- Search and filter by site/material/batch/state; all counts from database. Do not render synthetic random counts.

## Layout concept

```text
+----------------------------------------------------------------------------------+
| DON QualityOS | Global Search        | Plant / Region | Notifications | User    |
+----------------------+-----------------------------------------------------------+
| Quality Control Tower| Open Events     OOS            OOT           CAPA Backlog |
| Enterprise Master    |  [1,144]        [ ... ]        [ ... ]       [ ... ]      |
| Inspection Lots      +-----------------------------------------------------------+
| Laboratory Results   | Event Worklist: Site | Lot | Test | Value | Severity | SLA|
| Quality Events       |                                                           |
| Investigations       | Click event opens 3-column Object Page                    |
| QualisIQ Assistant   | Source Result | Investigation Tabs | Evidence / AI Panel   |
| CAPA / Audit         |                                                           |
+----------------------+-----------------------------------------------------------+
```

Numbers are **layout examples only**, not accurate seeded KPI values.
