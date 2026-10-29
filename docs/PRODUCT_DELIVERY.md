# QualisIQ product delivery — pharma QC / OOS / OOT

This increment turns the uploaded backend into a connected quality workbench. It is a tested development/pilot foundation, **not a production-approved or GMP-validated system**. The website uses actual authenticated API responses and actual synthetic database records. No manufacturer operational data was obtained, invented as real, or represented as a customer deployment.

## Capability map

The public design themes below come from the supplied blueprint. External pages could not be retrieved because the managed proxy blocked their domains; `source_checks.json` records attempts. These are engineering inspirations, not verified claims about competitors' current products.

| Theme | Delivered | Evidence / limit |
|---|---|---|
| SAP-inspired inspection traceability | Material → batch → inspection lot → sample → result → specification → event | New lineage read model + result-intake form; immutable source identities retained |
| Harmonized multi-site operations | Common worklist, site filters, per-site SQL counts, common controlled transitions | All 24 synthetic sites; tenant/site negative tests |
| Deviation / OOS / OOT investigation | Search/type/state filters; versioned investigation editing; role-controlled transitions | Browser tests cover editing + audited triage; original independent-QA tests retained |
| CAPA | Site-scoped worklist with due dates, linked cases, effectiveness metadata | Existing CAPA transition API retained; new screen is a read view |
| Evidence | Source fingerprints, source-linked deterministic checklist, evidence metadata | No raw-file storage/authenticity or real RAG index |
| Controlled documents | Tenant-global metadata register | Four synthetic metadata records; not complete SOP content or a document approval engine |
| ML triage | Reproducible Isolation Forest, training-only robust normalization, batch-disjoint calibration/evaluation, statistical baseline, JSON-only inference | Research-only; no demonstrated advantage over baseline; synthetic proxy labels |
| Security support | Same-origin app, memory-only browser tokens, issuer/audience/expiry checks, request IDs, host validation, security headers, login throttling | Throttling is per process; gateway controls and SSO remain required |
| Database lifecycle | Explicit Alembic baseline and drift check; disposable upgrade/downgrade tests | Existing preseeded DB must be inspected/backed up before stamping baseline; never blindly upgrade it |
| Deployment packaging | Multi-stage, non-root container; health/readiness endpoints; pinned Python/npm dependencies | Container validation outcomes recorded separately; not a public deployment |
| Recovery | Consistent SQLite backup, integrity check, foreign-key check and counts | Local demo only; no encrypted PostgreSQL recovery/RPO/RTO claim |

## Data and model truth

The supplied dataset contains **24 sites, 5,000 batches, 50,000 results, 1,192 events and 60 CAPAs**. Counts are database-backed. Existing approval states are simulated workflow states. The model uses only the supplied synthetic tenant. Public reference documents are not training rows. No real Sanofi/Cipla/SAP customer data, proprietary code, integrations, or endorsements are implied.

Training uses 3,000 batches, calibration 1,000, and test 1,000, ordered by batch manufacture timestamp then ID. These are disjoint batch groups; result timestamps can overlap. Normalization is fitted per specification on training rows only. Outcomes are excluded from inputs and used only as proxy evaluation labels. Unseen specifications abstain. The portable scorer is checked against scikit-learn; artifact checksum and dataset fingerprint are recorded. JSON artifacts do not execute pickle payloads.

At the conservative 1% calibration alert budget, held-out sensitivity is approximately **43.3%** (100/231 seeded exceptions), with 0/9,469 seeded negatives flagged. Zero observed false positives does not establish a zero real-world false-positive rate. The robust-Z baseline performs at least as well. Default model outputs cannot replace OOS/OOT rules and are disabled outside demo mode. The report includes 1%, 3%, and 5% alert-budget operating points. These are research scenarios, not approved thresholds. The evidence checklist is deterministic, not a live LLM.

## Required before a real customer production release

1. Obtain representative, licensed/de-identified QC history with independent labels, instrument/method metadata, and expert-reviewed intended-use acceptance criteria. Run temporal, held-out-site, subgroup, calibration, drift and adversarial validation. Do not tune on the final holdout or market synthetic metrics as clinical accuracy.
2. Integrate the customer's OIDC/SSO/MFA and session lifecycle, revocation, tenant provisioning and permission policy. Local JWT login is a demo mechanism. Enforce shared/distributed rate limits at the ingress gateway.
3. Perform a full threat model, permission audit, dependency/security review and penetration test. Add PostgreSQL row-level security where appropriate and validate concurrent writes/version conflicts under load. Sequential version checks are not a proved compare-and-swap concurrency guarantee.
4. Configure managed PostgreSQL, TLS, secrets/rotation, encrypted backups, restore rehearsals, monitoring, retention, incident response, RPO/RTO and deployment rollback. Local benchmarks are not service-level guarantees.
5. Store raw evidence in immutable encrypted storage with service-side hashing, malware scanning, retention and access controls. Hash-linked operational audit is not independent WORM storage. Implement trusted electronic signatures if required; seeded APPROVED states are not signatures.
6. Establish controlled product/method/site-specific statistical procedures, reviewed migrations, approved document versions, SOPs, validation traceability and independent qualification (IQ/OQ/PQ/UAT as applicable).
7. Connect authorized provider sandboxes before claiming SAP/LIMS/CDS/QMS integrations. Existing outbox records have no delivery worker or reconciliation SLA. Do not claim real RAG until licensed content, ACL-aware indexing and citation evaluation exist.

These remaining requirements need customer data, identity/deployment configuration and independent validation. No public deployment, remote push or environment publication was performed in this increment.
