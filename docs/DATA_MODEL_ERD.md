# Transactional data model (implemented starter)

```mermaid
erDiagram
  TENANT ||--o{ SITE : contains
  TENANT ||--o{ USER : employs
  TENANT ||--o{ MATERIAL : maintains
  SITE ||--o{ BATCH : manufactures
  MATERIAL ||--o{ BATCH : identifies
  MATERIAL ||--o{ SPECIFICATION : defines
  SPECIFICATION ||--o| OOT_PROFILE : calibrates
  BATCH ||--o{ INSPECTION_LOT : inspected_as
  INSPECTION_LOT ||--o{ SAMPLE : contains
  SAMPLE ||--o{ TEST_RESULT : produces
  SPECIFICATION ||--o{ TEST_RESULT : evaluated_against
  TEST_RESULT ||--o| ALERT : triggers
  ALERT ||--o| QUALITY_EVENT : opens
  QUALITY_EVENT ||--|| INVESTIGATION : owns
  QUALITY_EVENT ||--o{ EVIDENCE : references
  QUALITY_EVENT ||--o{ CAPA : generates
  TENANT ||--|| AUDIT_HEAD : integrity_chain
  TENANT ||--o{ AUDIT_LOG : traces
  TENANT ||--o{ OUTBOX_EVENT : publishes
  TENANT ||--o{ INTEGRATION_RECEIPT : deduplicates
```

The actual ORM source is `app/models.py`. This compact version is sufficient for demonstration but lacks mature product/method registries, enterprise organizational hierarchies, legal entities, source-version chains, electronic signature objects and full equipment provenance. Do not force unrelated external IDs into the same string namespace.
