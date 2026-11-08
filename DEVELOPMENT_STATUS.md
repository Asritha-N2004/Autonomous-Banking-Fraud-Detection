# Development status

## Implementation plan
1. Inspect repository and establish reproducible configuration (empty repository confirmed).
2. Implement database, validated API, authentication, roles and audit logging.
3. Generate explicitly synthetic, seeded temporal transaction data; add CSV ingestion.
4. Train and evaluate temporal ML baselines with past-only features.
5. Build temporal heterogeneous transaction graphs and investigation queries.
6. Implement typed hierarchical orchestration, parallel specialists and dependent review stages.
7. Persist evidence, investigations, human review and permission-controlled exports.
8. Build React/TypeScript dashboard using live API data.
9. Run backend/integration/frontend checks and reproducible evaluation.
10. Supply Docker configuration, operational documentation and limitations.

## Verification (2026-11-08)

| Phase | Implementation and observed verification |
|---|---|
| 1 | Empty repository inspected; plan created. Python 3.12 and Node 24 available. |
| 2 | SQLAlchemy schema, initial migration command, expiring sessions, password hashing, role checks, atomic ingestion and audit routes implemented. API tests passed. |
| 3 | Seed-42 generator produced and ingested 2,400 explicitly synthetic transactions. PaySim and BankSim user-supplied CSV adapters tested. No external dataset downloaded. |
| 4 | Trained calibrated logistic regression, random forest, gradient boosting and XGBoost, plus Isolation Forest and novelty LOF. Actual temporal results saved. Historical inference guard withholds estimates at/before calibration cutoff. |
| 5 | Built/persisted 2,712 entities and 16,800 evidence-bearing relationships. Centralities, communities, components, neighborhoods and paths implemented. Graph tests and browser path selection passed. |
| 6 | Supervisor plus eleven specialists implemented. Parallel analysis, dependent stages, validated references/provenance/uncertainty, bounded retries/deadline, failure disclosure and review checkpoint tested. |
| 7 | Twelve generated cases persisted, with evidence, risk breakdown, execution traces and reports. Review, notes, export and audit integration tests passed. No consequential banking action adapters exist. |
| 8 | Ten React/TypeScript dashboard sections use live backend APIs. Production build and nine frontend tests passed. Browser verified login, dashboard counts, narrow/desktop layout, graph selection and path highlighting. Screenshots in docs/screenshots. |
| 9 | Nineteen backend tests passed after temporal guard; nine frontend tests passed. Actual 480-record held-out benchmark, autoencoder/GraphSAGE experiment and 60-record ablations executed. See docs/model_evaluation.md. |
| 10 | README, research/security/API documentation, Mermaid architecture/workflow/ER diagrams, four notebooks, Dockerfiles and Compose supplied. Standalone `docker-compose config --quiet` passed. Docker engine is unavailable, so container builds/runtime and PostgreSQL integration remain unverified. |

No production readiness or real banking performance is claimed. Local backend successfully served on port 8017 (8000 belongs to a different pre-existing application); Vite proxy on 5173 served the verified dashboard. Owned preview servers are stopped after QA. Normal commands use port 8000; override the backend port and `API_PROXY_TARGET` if it is occupied.

## Actual outputs

- Synthetic demo: 2,400 ingested transactions; 12 distinct analyzed transactions; 12 awaiting-review cases; 3 unverified alerts; 2 high-priority cases; zero human-confirmed outcomes.
- Random forest held-out PR-AUC .9673, precision 1.0000, recall .8000. Logistic regression PR-AUC .9267; gradient boosting .9405; XGBoost .8695; Isolation Forest .6935; LOF .0778.
- Autoencoder PR-AUC .3477; GraphSAGE 1.0000 (offline synthetic experiment only).
- Full ablation sample: 60 records, four positives, six specialist evidence items per case. No investigator workload study was run.
- Tests: 19 backend + 9 frontend passing; minor scikit-learn small-class calibration warnings in the small training-test fixture. Frontend build warns about a large bundled graph/chart chunk.

## Pending or deliberately bounded

- Docker build/runtime and PostgreSQL execution cannot be verified without a running engine. Docker Desktop/service is not installed at the standard location in this environment.
- External licensed dataset retrieval/benchmarking, real-world banking validation, multi-seed statistical evaluation, validated protected-group fairness and prospective investigator studies remain pending.
- Optional autoencoder/GNN artifacts are real offline experiments; production API model selection supports the three core supervised models. XGBoost is trained/evaluated but not selectable for API scoring in this initial UI.
- Advanced tests ran with available PyTorch 2.13.0+cpu and pinned PyG 2.6.1. The portable optional requirements pin PyTorch 2.7.0; that separate pin has not been installed/verified here.
- Retention is configured/reported but purge/legal holds are not implemented. No deletion API is exposed.
- Audit storage is relational and access controlled, not externally tamper evident. Rate limiting is per-process, not distributed. HTTPS and encryption at rest require deployment configuration.
- Initial schema migration is implemented; future schema upgrades need new explicit migrations. No automatic destructive migration is performed.
- Background queue, streaming transport, real-time autonomous ingestion triggers, force-killable tool isolation and safe concurrent model registry publication are not implemented. Synchronous ingestion and analysis simulate monitoring locally.
- Device relationships are observed, not verified identity. No IP or protected demographic features are collected. No regulation-specific compliance guarantee is claimed.

## Local verification notes

Windows sandbox restrictions initially stalled asyncio loopback sockets; relevant API tests/builds ran successfully with authorized sandbox escalation. npm was unavailable in this shell; bundled pnpm installed dependencies and direct Node commands ran build/tests. Requirements were subsequently verified in a local virtual environment using pinned core packages rather than relying on preinstalled newer versions. A generated random administrator password is private in ignored `.env`; no credentials are committed. A temporary synthetic read-only browser QA user is removed after verification.

## Decisions
Use an explicit bounded state machine (permitted alternative to LangGraph). Core analysis requires no LLM.
SQLite locally; SQLAlchemy database URL for PostgreSQL. Separate optional deep learning dependencies.
Local repository deployment with Docker Compose; no externally hosted mock dashboard.

## Follow-up: Create account (2026-11-08)

Added a Create account option to the sign-in page and opened it in the live dashboard. Registration validates usernames and password confirmation, creates only Analyst accounts, hashes passwords, establishes an HTTP-only session and records an audit event. Duplicate usernames are rejected case-insensitively; role injection is rejected. Authentication rate limits also cover registration. Added five API tests and four form tests. Production frontend build passed; all 24 backend tests and 13 frontend tests passed. Browser verified the empty registration form; no account or password was created on the user's behalf. Local preview servers remain running at the user's request (frontend localhost:5173, backend 127.0.0.1:8017).

## Follow-up: Simplified usernames (2026-11-08)

Removed the username regular expression and three-character minimum from API and form. Nonempty names, spaces, emails, punctuation and Unicode are accepted up to the database limit of 80 characters. Whitespace-only names remain invalid; normalized duplicate checks remain. Sign-in now trims and matches case-insensitively. Seven focused registration/authentication tests and all 14 frontend tests passed; production build verified. Updated the running backend without navigating away from the user's open form.

## Follow-up: Vercel deployment (2026-11-08)

Created `resum-projects/sentinel-banking-fraud` and configured Vite/FastAPI as separate Vercel Services. Validated `vercel.json` against the official schema. Corrected an oversized first build by excluding the deployment-tool cache and using Linux CPU-only XGBoost. The corrected remote preview is READY at https://sentinel-banking-fraud-2s59gtaz9-resum-projects.vercel.app (342.08 MB Python bundle). Preview authentication protection is preserved.

Database-backed operation and production promotion remain incomplete. Automatic approval review rejected creation of a dedicated free Neon resource because explicit authorization for a new external database was missing. No resource was created, no paid plan chosen, and no provider terms accepted. The pending proposal is `sentinel-banking-fraud-db`, free_v3, iad1, for this project only; existing user-supplied PostgreSQL is an alternative. See docs/vercel_deployment.md for the concrete remaining setup.

Added hosted PostgreSQL URL normalization, fail-fast rejection of hosted SQLite, serialized schema/bootstrap setup, optional synthetic seeding, exact Vercel-origin handling and read-only hosted models. Full backend suite passed 25 tests after the first cloud adaptations; three targeted cloud/origin tests passed after the final changes. The last origin/startup refinements are local and require the next deployment once the database decision is resolved. No local user database or credentials were uploaded.

## Follow-up: Hosted request failure

Vercel runtime logs confirm startup fails because the persistent PostgreSQL DATABASE_URL is missing. The project environment variable list is empty; authentication/account creation cannot work until the hosted database and required server settings are configured. Database provisioning remains pending explicit user approval after the earlier automatic-review rejection; no new resource was created. A diagnostic vercel curl automatically created one automation bypass; it was immediately revoked through the documented API, and unchanged SSO/deployment protection was verified. Avoid vercel curl for future diagnosis unless that side effect is explicitly intended.

## Follow-up: Free Neon connected; production sign-in fixed

The user explicitly authorized the new free database. Provisioned and connected `sentinel-banking-fraud-db` on `free_v3`, region `iad1`, to this project only. Initialized PostgreSQL schema, roles, hosted administrator and 2,400 synthetic transactions; local accounts were not copied. Published production deployment `dpl_9DBGCX5UEnVzCMQHEn9KxNgUE59E` at https://sentinel-banking-fraud.vercel.app/. Verified public frontend/health, administrator sign-in, Secure/HttpOnly cookies, authenticated identity/dashboard/model reads, persistence, logout revocation, and sign-in again with normalized username. All expected HTTP statuses passed. Browser verified and opened the new production login page. Private hosted administrator credentials are in ignored `.vercel/cloud-admin.env`; connection settings in ignored `.vercel/cloud.env`. No secrets are in the public verification report.

An expanded production test plan was rejected by automatic review because it would create test accounts and investigations; a safer verification using the existing administrator and read-only application data completed successfully instead. No test production accounts or cases were created. Full local backend suite: 27 passing tests. Registration is covered by existing local tests; no live test account was created. Documentation now points to the permanent production URL; the old unconfigured immutable preview is superseded.

## Follow-up: Post-sign-in analytics request failure

Reproduced production HTTP 500 errors on transaction-trends and fraud-trends after a successful login; other initial dashboard requests returned 200. Direct read-only PostgreSQL reproduction confirmed a GroupingError: separately constructed substr expressions produced different SQL bind parameters in SELECT and GROUP BY. SQLite tests had not exposed the PostgreSQL-specific behavior. Reused one date expression for selection/grouping/ordering in both queries, then verified the queries on the actual dedicated PostgreSQL database: 34 daily groups totaling 2,400 transactions, and a valid empty fraud-trend result.

Changed initial dashboard loading to collect independent requests with Promise.allSettled and retain successful panels, with a named retry message for any failed panel. Added regression tests for daily counts/amounts/ordering and partial frontend failures. Backend suite: 29 passed; frontend suite: 15 passed; production frontend build passed. Production redeployment is in progress; final live verification follows before completion.

### Post-sign-in fix: production verification complete

Published `dpl_ApiAmHi6QmU6w8jduNDLjZZdq4HY` to https://sentinel-banking-fraud.vercel.app/. All eight initial/related authenticated API reads now return 200, including both previously failing trend endpoints. Transaction trend groups total 2,400 records across 34 days. Live results are recorded in docs/deployment_verification.json. Login and logout succeeded. No production test accounts or cases were created. Browser refresh/reattachment timed out, so final visual verification was unavailable; request-level production checks, PostgreSQL verification, 29 backend tests, 15 frontend tests and the frontend build passed. The user must refresh the open page to load the new bundle.
