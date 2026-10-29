# Automated verification matrix (demo only)

| Requirement | Implemented test |
|---|---|
| JWT required for private resources | `test_auth_and_no_auth` |
| OOS outside approved spec creates quality event | `test_oos_and_idempotency` |
| Retry does not produce duplicate events | `test_oos_and_idempotency` |
| Source ID/payload change rejected | `test_oos_and_idempotency` |
| Approved demo trend baseline raises OOT within spec | `test_oot_and_normal` |
| Missing baseline is explicitly not assessed | `test_missing_oot_baseline_is_unknown_not_pass` |
| Lot/batch/material lineage enforced | `test_master_lineage_and_role_permissions` |
| Invalid state transitions and role bypass rejected | `test_master_lineage_and_role_permissions`; `test_qc_qa_workflow_and_audit` |
| Independent QA review plus evidence reference | `test_qc_qa_workflow_and_audit` |
| Immutable approved/closed case transitions | `test_qc_qa_workflow_and_audit` |
| Different tenant cannot see event | `test_tenant_isolation` |
| Site-scoped role cannot ingest or view other sites | `test_site_scope_on_results_and_events` |
| Batch failure does not leave half-ingested records | `test_bulk_is_atomic` |
| Small atomic batch size guard | `test_bulk_has_limit` |
| Hash-chain validity and deliberate tamper detection | `test_qc_qa_workflow_and_audit`; `test_audit_change_detected` |
| CAPA effectiveness separated from action owner | `test_capa_independent_effectiveness` |
| AI brief references evidence and is not autonomous LLM | `test_ai_is_grounded_not_regulatory_decision` |

**Not covered:** concurrent ingestion races on PostgreSQL, OIDC, real encryption/WORM storage, database row-level security, backup restore, Part 11 e-signature qualification, deployed provider connectors, RAG quality and clinical/regulatory acceptance. These must be added before any regulated pilot.
