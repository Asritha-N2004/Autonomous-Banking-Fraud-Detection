# Sentinel: Autonomous Banking Fraud Investigation

**A Hierarchical Multi-Agent Agentic AI Framework for Autonomous Banking Fraud Detection and Investigation.**

A working local research application with FastAPI, SQLAlchemy, calibrated scikit-learn models, NetworkX, an explicit hierarchical state machine and a React/TypeScript dashboard. Eleven specialist agents turn transaction records into traceable investigation leads and structured reports. Human reviewers record outcomes. The system cannot transfer funds, restrict accounts, block transactions or notify external authorities.

This is a synthetic research prototype, not a validated banking product. See [development status](DEVELOPMENT_STATUS.md) for verification and remaining acceptance gaps.

## Quick start

Python 3.11/3.12, Node 22+ and npm or pnpm are required. Run from this repository root. No paid API or LLM key is needed.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
# Edit .env: set ADMIN_PASSWORD to a unique password of at least 12 characters.
python scripts/manage.py migrate
python scripts/manage.py bootstrap
python scripts/generate_synthetic_data.py
python scripts/ingest_data.py
python scripts/preprocess_data.py
python scripts/train_models.py
python scripts/build_graph.py
python scripts/manage.py demo
python -m uvicorn backend.app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [the local dashboard](http://localhost:5173) and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your private `.env`. An existing local `.env` may have been generated during verification; do not overwrite it accidentally. `.env` is automatically loaded with literal values only; environment variables take precedence. On Linux/macOS activate with `source .venv/bin/activate`.

Use **Create account** on the sign-in page to register an Analyst account. Usernames may be a simple name (including spaces), email address or other nonempty text up to 80 characters. They are normalized to lowercase, and sign-in ignores surrounding spaces and case; passwords require at least 12 characters and matching confirmation. Registration signs you in automatically and records an audit entry. Public registration cannot choose an elevated role; administrators create privileged accounts through the authorized user endpoint. Registration and sign-in share the authentication rate limit.

Alternatively, `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1` performs local data/model setup and generates a random password in `.env` if none exists. Run once against a new database. Duplicate ingestion is rejected, preserving existing records.

## What is implemented

- Relational persistence, indexed foreign keys, validated atomic ingestion, pagination and role/assignment access controls.
- Scrypt password hashes, expiring opaque HTTP-only sessions, logout revocation, same-site cookies, origin checks, per-process rate limiting and audit logs.
- Fixed-seed synthetic transactions, past-only account histories, equal-time feature isolation, temporal train/calibration/test splits.
- Logistic regression, random forest, gradient boosting; optional XGBoost; Isolation Forest and Local Outlier Factor. Supervised models are calibrated on a later validation interval. Local explanation is single-feature replacement sensitivity, explicitly not SHAP or a causal explanation.
- Optional offline PyTorch autoencoder and PyTorch Geometric GraphSAGE, with forward temporal edges and separate calibration.
- Heterogeneous evidence-bearing NetworkX graphs, degree/betweenness/PageRank, communities, components, neighborhoods and paths; graph snapshot persistence command.
- Six parallel specialists followed by evidence, risk, investigation, compliance and reporting; supervisor schema/provenance/reference checks, retries, deadlines and review checkpoint.
- Persisted cases, notes, assignments, documented supervisor review outcomes, provenance, execution traces, JSON/CSV/PDF exports.
- Ten live API dashboard sections, searchable/filterable/sortable transactions, React Flow explorer, Recharts trends and model evaluation.
- Offline experiment and ablation runner, tests, Docker Compose definition and documentation.

## Data and models

Default data: 2,400 explicitly synthetic records, seed 42. Generation labels are simulated historical outcomes, never real customer findings. Synthetic metrics can be deceptively high because the generator injects separable device and beneficiary patterns. Model predictions do not overwrite historical labels. Human outcomes are stored separately.

```powershell
python scripts/generate_synthetic_data.py --rows 2400 --seed 42
python scripts/import_dataset.py path/to/paysim.csv --kind paysim
python scripts/import_dataset.py path/to/banksim.csv --kind banksim
python scripts/import_dataset.py path/to/transactions.csv --kind canonical
python scripts/evaluate_models.py
python scripts/experiments.py --count 30
```

Import only datasets you are authorized to use. PaySim/BankSim adapters preserve simulator identities; their timestamps use an arbitrary documented reference epoch. Anonymized credit-card and IEEE-CIS data are not forced into fabricated account graphs. External datasets are not bundled or downloaded. [Dataset details](docs/dataset_documentation.md).

Optional advanced environment:

```powershell
python -m pip install -r backend/requirements-advanced.txt
python scripts/train_advanced.py --epochs 35
```

Advanced models are standalone offline experiments, not the default API prediction engine. Never load an untrusted `.joblib`/`.pt` file. Model training through the API is restricted to explicit synthetic data and administrators; controlled real-data training remains an offline responsibility.

## API

Interactive schema: [Swagger UI](http://localhost:8000/docs). Health: [health endpoint](http://localhost:8000/api/health).

```python
import httpx
with httpx.Client(base_url="http://localhost:8000") as client:
    client.post("/api/auth/login", json={"username": "admin", "password": "YOUR_PASSWORD"}).raise_for_status()
    result = client.post("/api/fraud/analyze", json={"transaction_id": "SYN-T000100"})
    result.raise_for_status()
    print(result.json())
```

Analysis is synchronous and bounded. `/api/agents/run` returns the persisted completed run ID rather than pretending to be a background job. Run status/log endpoints are for trace inspection. [API reference](docs/api_documentation.md).

For historical events at or before the model calibration cutoff, supervised probability is withheld to prevent hindsight scoring. Transaction, behavioral, account and graph evidence remains available; uncertainty discloses the missing model signal. The demo samples later test-period transactions by observed amount only.

## Tests and builds

```powershell
python -m pytest -q
cd frontend
npm test
npm run build
```

Synthetic tests cover validation, temporal leakage, graph evidence, orchestration failure recovery, permissions, review/audit and report formats. Frontend tests mock explicit synthetic API fixtures. Browser inspection, if completed, is recorded in development status. Evaluation results live in `models/baselines.json`, `models/advanced.json` and `models/experiments.json` after the respective commands. Metrics are measured from actual runs, not dashboard constants.

## Docker

Live Vercel app: [sentinel-banking-fraud.vercel.app](https://sentinel-banking-fraud.vercel.app/). A dedicated free Neon PostgreSQL database is connected; production health, authenticated dashboard reads, sign-in and logout are verified. See [Vercel deployment details](docs/vercel_deployment.md) for the private administrator credential location and update commands.

Set `ADMIN_PASSWORD` and `POSTGRES_PASSWORD` in `.env` (URL-encode special characters in a database URL password; a random hexadecimal value avoids ambiguity). Docker Desktop/Engine must be running.

```powershell
docker compose up --build -d
docker compose exec backend python scripts/manage.py migrate
docker compose exec backend python scripts/manage.py bootstrap
docker compose exec backend python scripts/generate_synthetic_data.py
docker compose exec backend python scripts/ingest_data.py
docker compose exec backend python scripts/train_models.py
docker compose exec backend python scripts/build_graph.py
docker compose exec backend python scripts/manage.py demo
```

If your Docker installation exposes standalone Compose, use `docker-compose` in place of `docker compose`. This environment has standalone Compose and no running Docker engine; configuration validation passed, container execution could not be verified.

Dashboard: [localhost:8080](http://localhost:8080). PostgreSQL is internal to Compose. Named volumes persist data/models. Local Compose uses HTTP and insecure-cookie transport on loopback; configure TLS termination and `COOKIE_SECURE=true` before any remote use. Do not expose the development stack directly to the internet. Docker execution status is recorded honestly in `DEVELOPMENT_STATUS.md`.

## Repository

```text
backend/app/
  main.py                 REST routes, auth, RBAC and exports
  database.py             relational entities and session factory
  schemas.py              validated transactions, settings and agent outputs
  security.py             passwords, sessions, permission helpers
  agents/                 supervisor and eleven specialist tools
  ml/                     generator, adapters, temporal features, training, inference, advanced models
  graph/                  heterogeneous graph, metrics, persistence and neighborhoods
  services/               ingestion and investigation persistence
backend/tests/            synthetic unit and API integration tests
frontend/src/             React dashboard, API client, styles and tests
scripts/                  setup, ingestion, training, graph and experiment commands
docs/                     architecture, research methodology, datasets, security and API
models/                   generated model artifacts and actual evaluation JSON
data/{synthetic,processed}/ generated datasets and graph metrics
notebooks/                reproducible analysis notebooks
docker-compose.yml        PostgreSQL, backend and frontend services
```

## Research limitations and next work

No external dataset benchmark, prospective investigator study, protected-group fairness validation or regulatory certification is claimed. Uncalibrated weighted priorities are separate from supervised probabilities and anomaly percentiles. Heuristic risk weights require institutional validation. Thread deadlines stop workflow consumption; Python threads cannot forcibly terminate a running native tool. Models are trusted local artifacts; concurrent multi-process model publication needs a registry and atomic swap. Local rate limiting and audit tables need a shared gateway and tamper-evident external storage for production. Retention is configured and reported; automated deletion/legal holds are not implemented. Database migration 1 bootstraps the current schema; future upgrades need explicit new migrations. Scaling, hardened deployment, external identity/SSO and real-data governance are further work.

Research directions: multi-seed external temporal benchmarks, calibrated GNN comparisons, causal explainability, validated network typologies, protected-group assessment where lawful, and randomized investigator workload/completeness studies.
