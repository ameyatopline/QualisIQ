# DON QualityOS — Flagship Enterprise Quality Backend (Demo v0.2)

**DON QualityOS** unifies a SAP-inspired inspection domain, a Cipla-style deviation/CAPA operating model, and Sanofi-style multi-site quality harmonization principles. **QualisIQ** is the evidence-linked OOS/OOT investigation assistant. These are independent design inspirations based on public materials; this is *not* SAP, Sanofi, Cipla, TrackWise or Veeva source code, nor a deployed/validated pharmaceutical system.

> **SYNTHETIC / NON-GMP.** Every batch, result, event, evidence and simulated QA workflow in the supplied database is generated. Do not use for real GMP decisions. The demo includes `APPROVED` quality-event workflow states, but they are not Part 11 electronic signatures or batch releases.

## What is implemented and verified

- API `/docs` (FastAPI Swagger), JWT demo login with 6 fictional roles, tenant and basic site authorization.
- Synthetic site/material/batch/inspection lot/sample and effective-dated specification/approved-demo-baseline schema.
- Source-record immutable identity, request hash, idempotency key and atomic 1–250 result ingestion.
- Deterministic OOS, illustrative baseline-driven OOT alerts, quality event + investigation creation.
- Controlled QC-to-independent-QA states, investigation edits, linked evidence metadata and CAPA transitions.
- SQL-aggregated dashboard counts, event list/detail, source-linked deterministic QualisIQ checklist, transaction outbox rows, hash-linked operational audit verification.
- Scripts: repeatable enterprise-scale generated dataset, illustrative case histories, CSV importer, dataset manifest.
- Automated test suite; run locally using SQLite or Docker Compose for PostgreSQL.

## Quick start — Mac/Linux

```bash
cd DON_QualityOS_Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# The zip already includes the 24-site / 50k-result demo SQLite database.
# To rebuild from scratch, delete the DB and run:
# python scripts/seed_enterprise.py --sites 24 --batches 5000 --results 50000
# python scripts/seed_workflows.py --cases 240
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs**, or **http://127.0.0.1:8000/health**.

Demo account: `qc_analyst@don-demo.test` and `qa_reviewer@don-demo.test`. Local password default: `DemoOnly!2026` (or override with `DEMO_PASSWORD` *before first seeding*). Never reuse demo credentials in any real environment.

Login:

```bash
curl -s http://127.0.0.1:8000/api/v1/auth/login \
 -H 'Content-Type: application/json' \
 -d '{"email":"qc_analyst@don-demo.test","password":"DemoOnly!2026","tenant_code":"DON-DEMO"}'
```

Copy `access_token` into the Swagger **Authorize** dialog. `demo_data/sample_ingest.json` is an OOS example; enter via `/api/v1/lab/results` while authorized. Check response `event_id`, open `/api/v1/quality/events/{event_id}`, then review investigation and AI brief.

CSV importer:

```bash
export DEMO_PASSWORD='DemoOnly!2026'
python scripts/import_csv.py demo_data/sample_results.csv
```

**Important:** The SQLite DB is a snapshot and the seeder is idempotent against the same tenant. To generate a new, *separate* experimental database, set `DATABASE_URL=sqlite:///./my_scale_test.db` and run the seed command. No real manufacturer identifiers are included.

## Docker (local development)

```bash
docker compose up --build -d
# First run: initialize synthetic data INSIDE the API container's PostgreSQL database.
docker compose exec api python scripts/seed_enterprise.py --sites 4 --batches 200 --results 2000
docker compose exec api python scripts/seed_workflows.py --cases 50
```

The Compose setup binds API and PostgreSQL to localhost and uses intentionally insecure development credentials. It is NOT a production deployment.

## Scale scenarios (generated, not verified production capacity)

| Mode | Sites | Batches | Results | Status |
|---|---:|---:|---:|---|
| Included starter | 24 | 5,000 | 50,000 | Actually generated |
| Enterprise test | 24 | 30,000 | 250,000 | Generator configuration, not yet benchmarked |
| Extreme load test | 100 | 150,000 | 1,500,000 | Planned generator/load target |

Generate next target in a clean, separate demonstration database:

```bash
DATABASE_URL=sqlite:///./don_enterprise_250k.db python scripts/seed_enterprise.py \
  --sites 24 --batches 30000 --results 250000 --seed 20261029
```

For measured throughput / concurrency, run using PostgreSQL and load tools; the generator's offline bulk insertion time is **not** an API-ingest performance benchmark.

## Tested API surface

`GET /health`; `POST /api/v1/auth/login`; `GET /api/v1/auth/me`; `GET /api/v1/master/sites`; `GET /api/v1/master/materials`; `GET /api/v1/lab/inspection-lots`; `POST /api/v1/lab/results`; `POST /api/v1/lab/results/bulk`; `GET /api/v1/lab/results`; `GET /api/v1/quality/events`; `GET /api/v1/quality/events/{id}`; `PATCH /api/v1/quality/events/{id}/investigation`; `POST /api/v1/quality/events/{id}/transition`; `POST /api/v1/quality/events/{id}/evidence`; `POST /api/v1/quality/events/{id}/capa`; `POST /api/v1/quality/capa/{id}/update`; `GET /api/v1/quality/events/{id}/ai-brief`; `GET /api/v1/analytics/overview`; `GET /api/v1/audit/verify`; `GET /api/v1/audit/events`; `GET /api/v1/integrations/outbox`.

## Documentation navigation

- `docs/ENTERPRISE_BLUEPRINT.md` — architecture, Sanofi/Cipla/SAP patterns, contexts, data authority and growth roadmap.
- `docs/SOURCE_CONNECTOR_CONTRACTS.md` — mapping SAP/LIMS/CDS/QMS/MES and source contracts; **not live provider integrations**.
- `docs/AI_VALIDATION_PLAN.md` — scientific rules, planned RAG and evaluation methods.
- `docs/SECURITY_GAP_REGISTER.md` — capabilities missing before GMP/production use.
- `docs/FRONTEND_API_HANDOFF.md` — SAP Fiori-style navigation and API wiring.
- `docs/CODEX_MASTER_PROMPT.md` — detailed next-iteration Codex instructions.
- `demo_data/DATASET_MANIFEST.json` — authoritative counts/claims about demo database.

## Local tests

```bash
pytest -q
```

## Future work (do not claim completed)

Alembic/HA Postgres, SAML/OIDC SSO/MFA, cryptographic e-signatures, fine-grained ABAC/RLS, immutable object storage, integrated raw CDS files, actual SAP/TrackWise/Veeva connectors, delivery workers, real RAG/LLM, validated statistical controls, APQR engine, reliable file retention, independent audit/WORM and full GxP system qualification.

### Research references

SAP: https://learning.sap.com/courses/applying-sap-s-4hana-quality-management/using-inspection-lots-and-quality-notifications-in-the-logistics-supply-chain_a0e23470-b5bb-4b30-b4b8-7e886a42df1c\
Sanofi: https://www.veeva.com/customer-stories/sanofi-driving-efficiency-and-growth-with-vault-quality/\
Cipla FY2022–23 annual report: https://www.cipla.com/sites/default/files/Annual-Report-FY-2022-23-Double-page.pdf\
FDA OOS: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/investigating-out-specification-oos-test-results-pharmaceutical-production-level-2-revision\
MHRA: https://www.gov.uk/government/publications/guidance-on-gxp-data-integrity
