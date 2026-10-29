# Codex master implementation handoff — DON QualityOS

You are the principal backend architect and pharmaceutical quality-systems engineer implementing **DON QualityOS**, a synthetic-data, SAP-inspired, multi-site pharmaceutical quality operating system. The AI module is **QualisIQ**.

## First actions

1. Read all: `README.md`, `docs/ENTERPRISE_BLUEPRINT.md`, `docs/SOURCE_CONNECTOR_CONTRACTS.md`, `docs/AI_VALIDATION_PLAN.md`, `docs/SECURITY_GAP_REGISTER.md`, then inspect the existing `app/`, `tests/`, and `scripts/` code.
2. Run tests: `pytest -q`. Start API and inspect `/docs` plus the actual preseeded synthetic database. Do not rewrite a tested implementation as disconnected scaffolding or mock pages.
3. Report accurately what's implemented (real endpoint + DB-backed), what is simulated, and what is not started. Do not claim Part 11/GMP compliance, real SAP/Veeva/TrackWise connectivity, model accuracy, or production SLA without evidence.
4. Keep all generated demo data labeled synthetic. Never impersonate real manufacturers, issue fabricated QA/electronic signatures, or convert simulated analytical outcomes into real batch-release decisions.

## Product scope — adopt strengths, not proprietary code

- **SAP S/4HANA QM**: material/site/batch/inspection lot/sample/specification/test result/defect/quality notification relationships; source-controlled identifiers; flexible worklists and Object Pages via UI5 React.
- **Sanofi-style harmonization**: common configurable quality workflows across multiple sites, shared/global vs local SOP and method versions, versioned controls, document/training relationships, integration and warehouse-ready event streams, fast-track candidates that remain QA-controlled.
- **Cipla-style digital QMS**: deviations, laboratory incidents and nonconformance, OOS/OOT, CAPA, complaint/audit integration, stability/QC trending, APQR-ready reporting.
- **QualisIQ**: rules + product-specific statistics + optional ML + RAG grounded on authorized evidence; independent human approval.

## Recommended architectural direction

Keep a **modular monolith first** (Python FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Redis/Arq or Celery, S3-compatible object storage, OpenTelemetry). Extract services only when proven useful. React TypeScript and SAP UI5 Web Components serve the frontend. Use an explicit outbox + adapter strategy for external systems. Design multi-tenancy and site scoping from day one; database row-level security in PostgreSQL is desirable defense in depth.

## Phase-by-phase engineering tasks

### P0 — Make the starter secure and supportable
- Preserve the working tests and complete code review. Replace `create_all()` schema management with reviewed Alembic migrations. Add developer setup and pre-commit CI. Improve error model (problem details RFC 9457), field-level validation, offset pagination and filterable worklists.
- Harden role/plant scoping with complete permission matrix, site ownership for CAPA/evidence/audit, middleware request IDs, strict CORS, rate limiting, CSRF handling when browser cookies are used, structured security logs, secrets/config validation and test isolation.
- Resolve gaps in `docs/SECURITY_GAP_REGISTER.md` in tracked issues, not by renaming things compliant.

### P1 — Full SAP-style transactional object graph
- Build CRUD with authorization, versioned master data, approval gates and source-entity mapping for legal entity, site/plant, material/product, batch, inspection lot, sample, analytical method, test characteristic, specifications (effective dating, no overlaps), and calibration-equipment registry.
- Source IDs and revisions must survive mapping without silent substitutions. Never assume SAP APIs are available until a sandbox is connected.

### P2 — Reliable multi-source ingestion
- Implement integration connector SDK with normalized envelopes, payload schemas, field mapping and validation, immutable raw landing zone, idempotency, reconciliation, dead-letter queue, source lineage, observed_at vs effective_at, quarantine and observable retry workers.
- Start with CSV, generic LIMS result JSON, `SYNTHETIC_CDS` raw-data metadata. Use SAP QM documented APIs once access exists. Add provider-specific connectors only with genuine authorization/sandbox, not fake HTTP responses.

### P3 — Controlled quality event engine
- Implement typed event families: OOS, OOT, deviation, laboratory incident, laboratory nonconformance, complaint, supplier issue, change control, equipment exception. Formal transitions for Phase I, Phase II, OOT, QA independent review, CAPA effectiveness and closure.
- Add per-plant workload queues, SLA/escalation, reason codes, immutable revisioning and complete traceable report views. Distinguish investigation approval, SAP inspection usage decision and batch release as separate actions.

### P4 — QualisIQ AI and trending
- Implement approved-limit comparison, SOP-specific OOT control limits, long-term stability/retention, robust trend plots and explicit not-assessed outcomes. Build evaluation datasets with ground-truth labels and false-positive/sensitivity reporting.
- Add ACL-scoped RAG: controlled SOPs, methods, instrument calibration, BMR, previous investigations, LIMS/CDS evidence. Source/citation links for *every factual finding*. Return hypotheses and evidence gaps, not an AI root-cause verdict. No AI-initiated retesting, OOS invalidation, specification changes, QA signoff or release.

### P5 — Frontend and data visualization
- Convert existing `INTERACTIVE_WIREFRAME.html` from prior package into UI5 React workbench. Navigation: Quality Control Tower, Enterprise Master Data, Inspection Lots, Results, Exceptions, Investigation Object Page, Evidence, CAPA, Controlled Docs, QualisIQ Assistant, Analytics/APQR, Integrations, Audit/Administration.
- Each view backed by real API/filtered data; no hardcoded KPI cards. Every simulated record must have synthetic watermark. Include clear links from each quality alert to test result→lot→batch and evidence.

### P6 — Observability / validation / scale
- Add integration tests for idempotent retries, partial failures, race conditions, exactly-once logical outcomes, multi-tenant isolation, site privilege escalation, audit tampering, signature policy, expired specs and stale approvals.
- k6/Locust load tests with 250,000 and then 1,500,000 synthetic results; report measured p50/p95/p99 latency and throughput. Instrument Prometheus/OpenTelemetry, outbox queue lag and DB query plans. Validate backup restoration and documented failover.
- Create GxP validation documentation **only as draft templates**; the implementation is not a validated regulated system until documented independent qualification and controlled deployment.

## Current seed and demonstration

- Local seeded DB: 24 synthetic sites, 5,000 batches, 50,000 results, 1,192 flagged cases (manifest contains exact state counts), 240 selected case histories. More data is supported by `python scripts/seed_enterprise.py --sites 24 --batches 30000 --results 250000` against an intentionally separate demo database.
- Local demo users: `qc_analyst@don-demo.test`, `qc_manager@don-demo.test`, `qa_reviewer@don-demo.test`, `qa_head@don-demo.test`, `admin@don-demo.test`, `auditor@don-demo.test`; demo password configured using `DEMO_PASSWORD` (never copy these to production).

## Acceptance criteria for the next Codex increment

- `pytest -q` green, plus authorization/invalid-input tests for each new route.
- Existing result import→approved spec→OOS/OOT→alert→investigation→independent QA flow remains functional.
- No silent source overwrite, no cross-tenant leakage, no unrecorded state changes, no model-made regulatory decisions.
- Enterprise screens show SQL-backed counts, meaningful filters and links; realistic synthetic narratives never masquerade as real batch release records.
- Output a clear implementation matrix (done vs simulated vs blocked), actual test counts, local run commands, DB migration notes and next PR-ready milestone.

**Proceed with code changes in the current local workspace. Do not push to external remote systems or touch real enterprise data without explicit request and access.**
