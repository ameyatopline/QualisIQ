# Critical gap register (must resolve before real pharmaceutical production)

The shipped backend is an educational local demo with useful controls, **not production/GMP-ready**, despite enterprise-inspired design. Never deploy it with real GMP data or public internet access as-is.

| Priority | Feature today | Missing production control |
|---|---|---|
| P0 | Local PBKDF2 + demo JWT | Corporate SSO/OIDC, MFA, token revocation/rotation, session policies, rate limits, secure secrets management |
| P0 | Tenant/site filters in main endpoints | Formal ABAC/RBAC authorization matrix, row-level security, site-scoped audit access, permission-negative tests across every route |
| P0 | Application-generated SQLite schema | Alembic migrations, change approvals, rollback, checked migration histories, PostgreSQL HA |
| P0 | Hash-linked operational audit | Immutable independent/WORM audit storage, separate admins, trusted clock, retention, alerting, backup verification |
| P0 | `approved_by` demo user field | Validated electronic-signature workflow (21 CFR Part 11, where applicable), identity re-auth, signature meaning and record association |
| P0 | Metadata-only evidence with supplied SHA | Cryptographic content hashing performed by the service, immutable versioned encrypted storage, retention, legal holds and malware scanning |
| P0 | OOT demo z score and artificial spec baselines | Approved product/method-specific OOT procedures, historical representativeness and independent validation |
| P0 | Deterministic evidence checklist | RAG source ACLs, grounding validation, model lifecycle, evaluation, AI disclosures, prohibited AI actions |
| P1 | Outbox rows stored | Outbox worker, retries, dead-letter queue, delivery reconciliation, ordering and monitoring |
| P1 | Aggregate dashboard | Precomputed analytical model, page-level filters, time-series partition plan, stress and correctness benchmarks |
| P1 | No operational backups | Encrypted backups, documented RPO/RTO, restore drills, point-in-time recovery and business continuity |
| P1 | Demo-only one-tenant fixtures | Tenant provisioning, legal entity data retention and shared services hardening |
| P1 | No dedicated security review | Dependency checks, SAST/DAST, threat modeling, pen tests, incident response, secure SDLC |
| P1 | No GxP validation | Intended-use specification, GxP risk assessment, URS/FS/DS, traceability, IQ/OQ/PQ/UAT, change controls, SOP and vendor qualification |

The status `APPROVED` on seeded quality events is a **simulated human workflow state**, not an e-signature, legal signoff or batch disposition.
