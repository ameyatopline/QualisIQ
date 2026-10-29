# QualisIQ — connected pharmaceutical quality intelligence

A FastAPI + React/TypeScript quality workbench built on the uploaded DON QualityOS backend. Includes a real synthetic dataset, QC result intake, traceable OOS/OOT investigations, site analytics, CAPA worklists, controlled-document metadata, public source references, and an evaluated research anomaly model.

**Synthetic / non-GMP. Development and pilot foundation; not production/GMP approved.** See [delivery and release requirements](docs/PRODUCT_DELIVERY.md) and [security gap register](docs/SECURITY_GAP_REGISTER.md). No real manufacturer data or proprietary integration is bundled.

## Run locally

Requires Python 3.12, Node 24, and npm. The supplied demo database is retained in the workspace and delivery ZIP but intentionally excluded from Git. The commands below generate it for a fresh clone while preserving an existing copy.

```bash
cd QualisIQ  # In the cloud workspace: cd /workspace/QualisIQ
make install
if [ ! -f don_qualityos_demo.db ]; then
  APP_ENV=demo DATABASE_URL=sqlite:///./don_qualityos_demo.db .venv/bin/python scripts/seed_enterprise.py --sites 24 --batches 5000 --results 50000
  APP_ENV=demo DATABASE_URL=sqlite:///./don_qualityos_demo.db .venv/bin/python scripts/seed_workflows.py --cases 240
fi
make model
make dev
```

The website and API are served by FastAPI on port 8000. `make dev` builds the website before starting the API. The development alternative is API on port 8000 and `npm --prefix frontend run dev` on Vite's port; its proxy forwards `/api` to FastAPI. The website uses memory-only tokens, so a reload requires login again.

Demo accounts: `qc_analyst@don-demo.test`, `qc_manager@don-demo.test`, `qa_reviewer@don-demo.test`, `qa_head@don-demo.test`, `auditor@don-demo.test`, `admin@don-demo.test`. Tenant: `DON-DEMO`. Password for the supplied synthetic DB: `DemoOnly!2026`. These are public demo credentials, never production credentials. Changing `DEMO_PASSWORD` does not change already-seeded passwords.

`.env.example` documents variables; the API reads the process environment. It does not automatically load a `.env` file. Configure `ALLOWED_HOSTS` to the intended hostnames when serving behind a gateway; do not use a wildcard. No LLM key or external service is needed for the local workflow.

### Interface and motion

The workbench uses the installed [apple-design skill](.agents/skills/apple-design/SKILL.md): translucent navigation and object-page sheets, system typography, blue enterprise controls, and compact worklists. Decorative subtitles and KPI captions have been removed. Data labels, provenance, validation messages and synthetic-data disclosures remain visible.

The investigation sheet supports rightward drag dismissal, spring return when released before dismissal, and Escape/close-button dismissal with native dialog focus handling. Navigation and segmented investigation tabs use shared spring transitions. Reduced-motion, reduced-transparency, higher-contrast and forced-color preferences have explicit fallbacks. No external font download is required.

[Control tower](docs/screenshots/control-tower-desktop.png) · [Sign-in](docs/screenshots/sign-in.png) · [Investigation sheet](docs/screenshots/investigation-glass.png) · [Mobile](docs/screenshots/control-tower-mobile.png) · [UI validation](docs/UI_REDESIGN_VALIDATION.json)

After pulling frontend updates, run `npm --prefix frontend ci` followed by `npm --prefix frontend run build`, then restart the backend and refresh the browser. Frontend dependencies include Motion; the backend API and database schema are unchanged by this redesign.

### Database location

By default, the SQLite database is the file `don_qualityos_demo.db` in the folder from which you start the backend (normally the repository root). The signed-in workspace displays the actual active SQLite file path beneath the page title. In-memory databases have no file. When using PostgreSQL or production mode, connection details remain hidden; the database is stored on the configured database server. Override the backend connection with the `DATABASE_URL` process variable.

### First workflow

Sign in as QC analyst → Result intake → select an authorized inspection lot → record Assay `93.5 %` with a unique source ID → open the generated OOS case → inspect Lineage and Intelligence → complete investigation draft → record permitted workflow steps. QC-manager/independent-QA gates remain server-enforced. Intelligence outputs are advisory; no AI batch disposition exists.

Use Control tower for database-backed metrics, charts and filtered worklists. Site network opens per-site cases. CAPA and document screens display actual stored metadata. Source library distinguishes reference links from imported content. The model screen shows measured performance against a baseline and limitations.

### Investigation graphs

Open an investigation → **Analysis** (or **View OOS / OOT graphs** on Overview). Each case has a specification-limit graph and a stored-baseline Z-score graph, with a highlighted case result, 20/40/80-result comparable-history windows and exact source data. Missing or invalid baselines remain not assessed. See [graph definitions and examples](docs/INVESTIGATION_GRAPHS.md). No reseeding or schema migration is needed.

## Validation

```bash
make check
make e2e
.venv/bin/python scripts/train_model.py
.venv/bin/python scripts/benchmark_api.py --url http://127.0.0.1:8000
.venv/bin/python scripts/backup_database.py --output artifacts/backups/new-demo-backup.db
.venv/bin/python scripts/validate_postgres.py
```

Browser tests require a Chromium executable (`/usr/bin/chromium`, or set `CHROMIUM_PATH`); they start an isolated server with a disposable copy of the supplied DB. They do not edit the main demo database. PostgreSQL validation requires the managed local Docker socket and starts/removes only its own ephemeral container. Benchmark defaults to port 8010 unless `--url` is supplied. Results describe local checks only.

Python versions are pinned in `requirements.lock`; npm uses `frontend/package-lock.json`. `requirements.txt` describes compatibility ranges. The repository includes the training code; `artifacts/` is Git-ignored. Rebuild the model using `make model`. The full report and portable JSON model are retained in this workspace/delivery ZIP.

## Database lifecycle

New empty database: set `DATABASE_URL`, then `.venv/bin/alembic upgrade head`. Verify with `.venv/bin/alembic check`. Demo startup retains `create_schema()` for the supplied starter database; production startup does not create schemas. Do not run baseline `upgrade` against an already-populated unstamped starter DB. Back it up, compare its schema to the baseline, and only then stamp the matching baseline after review. Never use schema stamping to skip an actual migration.

To regenerate a missing demo database, use an intentionally new DATABASE_URL:

```bash
DATABASE_URL=sqlite:///./new-demo.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:///./new-demo.db .venv/bin/python scripts/seed_enterprise.py --sites 24 --batches 5000 --results 50000
DATABASE_URL=sqlite:///./new-demo.db .venv/bin/python scripts/seed_workflows.py --cases 240
```

This creates a new deterministic dataset, not manufacturer data. Preserve the supplied DB for reproducible tests and model evaluation.

## Container packaging

```bash
docker build -t qualisiq:local-review .
docker compose up --build -d
```

In a managed environment with a session CA, pass `--secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt` to the build. The Dockerfile mounts the CA only during package installation; TLS verification remains enabled. Compose requires equivalent build-secret configuration in that environment (see compose file). Seed the empty container database using the commands in [the original starter guide](docs/STARTER_README.md). The image runs as a non-root user and excludes local DBs, secrets, node_modules, model artifacts and Git metadata. No demo model is automatically enabled in a production deployment.

`APP_ENV=production` requires a unique JWT secret, PostgreSQL URL, and explicit hostnames. Those guards do **not** confer production readiness: SSO, signatures, independent audit storage, operational controls and external qualification are still outstanding. The research-model routes fail closed outside demo mode. `/health` is liveness; `/ready` checks database/schema access.

## Evidence and design references

- [Product delivery / capability matrix / production gates](docs/PRODUCT_DELIVERY.md)
- [Source retrieval attempts](docs/source_checks.json)
- [Local read benchmark](docs/LOCAL_BENCHMARK.json)
- [Scientific model plan](docs/AI_VALIDATION_PLAN.md)
- [Enterprise blueprint](docs/ENTERPRISE_BLUEPRINT.md)
- [Original starter documentation](docs/STARTER_README.md)

The project adopts public design ideas associated with inspection traceability, multi-site harmonization and digital deviation/CAPA management. It is independent software, not an SAP, Sanofi, Cipla, Veeva or TrackWise product. Public links are metadata; blocked pages were not read or used as training data.
