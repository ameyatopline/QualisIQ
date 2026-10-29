# Enterprise data connectors — blueprint (not live integrations)

## System-of-record strategy

| External system | Representative input | Mapping into DON QualityOS | Status |
|---|---|---|---|
| SAP S/4HANA QM | Inspection lot, operations, status, material and batch identifiers | Material/Batch/InspectionLot; preserve SAP IDs as external references | **Mapped in design only** |
| LIMS (Thermo SampleManager, LabWare, Veeva, etc.) | Sample IDs, specifications, analyte, result, analyst, instrument, status | Sample, Specification, TestResult | **Generic typed API implemented; provider connector pending** |
| CDS (Waters Empower, Agilent OpenLab, etc.) | Instrument raw-data metadata, chromatogram archive URI, integration summary | Result source ID and Evidence references | **Contract only** |
| QMS (TrackWise, Veeva) | Deviation, investigation, CAPA and review status | QualityEvent, Investigation, CAPA, external ID map | **Contract only** |
| MES/BMR | Production order, batch step, deviations | Batch and batch-associated evidence | **Contract only** |
| Calibration/CMMS | Instrument asset, calibration, maintenance | Equipment snapshot and hypothesis evidence | **Future module** |
| Stability system | Product, timepoint, storage conditions, numerical trending | OOTProfile plus stability series | **Future module** |
| Public FDA/MHRA/ICH references | Guidances, standards, URLs, issue versions | Permission-safe regulatory knowledge register | **Curated links in docs; no copyrighted full-text import** |

## Normalized result payload — existing endpoint

POST `/api/v1/lab/results`

```json
{
  "site_code":"DQ-001",
  "material_code":"DON-MAT-001",
  "batch_number":"DON-SYN-B-0000001",
  "inspection_lot":"DON-SYN-L-0000001",
  "sample_number":"DON-SYN-S-0000001",
  "test_name":"Assay",
  "value":"93.7",
  "unit":"%",
  "measured_at":"2026-10-29T10:00:00Z",
  "source_system":"SYNTHETIC_CDS",
  "source_record_id":"CDS-DEMO-9999",
  "idempotency_key":"CDS-DEMO-9999-IMPORT-1"
}
```

- 201 with `result_id`,`outcome`,`event_id`,`specification_version`. Retries use the same `idempotency_key`; a changed payload with the same key is rejected.
- Material, batch, lot and sample must already exist in master data and match the same site and tenant.
- Approved effective specification and exact unit are required. No silent unit conversion.
- `POST /api/v1/lab/results/bulk` atomically processes 1–250 normalized rows; does not mean provider-specific connectors exist.

## Proposed source envelope (future)

```json
{
  "schema_version":"1.0",
  "source": "SAP_QM",
  "tenant_external_id":"DON-DEMO",
  "object_type":"inspection_lot",
  "external_record_id":"000000000000001234",
  "external_revision":"1",
  "source_event_time":"2026-10-29T08:15:00Z",
  "ingested_at":"2026-10-29T08:16:05Z",
  "idempotency_key":"SAP_QM/1234/v1",
  "content_sha256":"<sha256-of-canonical-payload>",
  "payload":{"lot_number":"1234","material":"000001","batch":"LOT-A","status":"OPEN"}
}
```

Production mapping needs endpoint configuration, credentials, polling/webhook strategy, signed messages, retries, ordering, de-duplication, version tracking, schema contracts, failure DLQ, tenancy and reconciliation jobs. **Never write a supplier SDK or label a demo mapping as a tested SAP connector without access to a documented integration sandbox.**

## Background event delivery (future)

`quality_event.created`, `quality_event.status_changed`, `capa.effectiveness_pending`, `document.revised`, `trend.baseline_updated`.

The transactional outbox table already records `quality_event.created` and status changes. No worker delivers them yet. Build an idempotent worker and DLQ; keep cross-system updates pending/reconcilable. Do not post closed-case or approved-batch status back into ERP automatically.
