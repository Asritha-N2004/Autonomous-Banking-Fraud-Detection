# API reference

Run backend then open `/docs` or `/openapi.json` for current request schemas. All routes except `/api/health`, login and registration require authenticated session or a valid previously issued bearer token. Browser login returns a secure-policy-controlled HTTP-only cookie, never a localStorage credential. Documentation endpoints are accessible locally; place behind perimeter access if deployed.

| Area | Routes |
|---|---|
| Auth/users | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `GET/POST /api/users` |
| Registration | `POST /api/auth/register` with username, password and confirm_password; creates only ANALYST and sets an authenticated session cookie |
| Transactions | `POST/GET /api/transactions`, `POST /api/transactions/batch`, `GET /api/transactions/{id}` |
| Fraud | `POST /api/fraud/analyze`, `GET /api/fraud/alerts`, `GET /api/fraud/alerts/{id}`, `GET /api/fraud/statistics` |
| Cases | `POST/GET /api/investigations`, `GET/PATCH /api/investigations/{id}`, `POST .../{id}/notes`, `POST .../{id}/review`, `GET .../{id}/report?format=json|csv|pdf` |
| Evidence | `GET /api/evidence?case_id=...&offset=0&limit=100` |
| Agents | `POST /api/agents/run`, `GET /api/agents/runs`, `GET /api/agents/status/{id}`, `GET /api/agents/logs/{id}` |
| Graph | `GET /api/graph/statistics`, `GET /api/graph/neighborhood/{node_id}?hops=1`, `GET /api/graph/relationships/{node_id}`, `GET /api/graph/path?source=...&target=...`, `GET /api/graph/investigation/{case_id}` |
| Models | `GET /api/models`, `GET /api/models/metrics`, `POST /api/models/train`, `POST /api/models/evaluate` |
| Analytics | `GET /api/analytics/dashboard`, `GET /api/analytics/transaction-trends`, `GET /api/analytics/fraud-trends`, `GET /api/analytics/agent-performance` |
| Administration | `GET/PATCH /api/settings`, `GET /api/audit` |

Analysis request: `{"transaction_id":"SYN-T000100"}`. Returns persisted case ID, run ID, priority, category and awaiting-review status. It runs synchronously; no false asynchronous completion promise. Each invocation can create a new investigation snapshot; alert counts count investigations, while analyzed-transaction counts count distinct records. Transactions are not automatically investigated on ingestion, allowing explicit batch review decisions. Script `manage.py demo` creates a bounded sample based on observed amounts, not labels.

Transactions list supports `q`, `channel`, whitelisted `sort=timestamp|amount|id`, `direction=asc|desc`, `offset` and `limit` (max 100). Case/alert/evidence/audit lists are bounded and paginated. Graph IDs use prefixes such as `account:SYN-A000`; neighborhoods are capped at 180 nodes and disclose truncation. Graph snapshots accept `as_of` for temporal investigation; case graphs are automatically constrained to event time.

Review body includes `outcome=confirmed_fraud|false_positive|inconclusive`, `decision=approve_recommendation|reject_recommendation|request_more_information`, and rationale of at least 10 characters. More-information decisions keep case in progress. Other decisions close with a recorded outcome. Closed cases cannot have status/outcome rewritten.

Errors: 401 missing/invalid session, 403 role/assignment/origin denial, 404 missing record, 409 duplicate or closed-case conflict, 422 invalid inputs, 429 rate limit, 503 incomplete investigation. Unexpected server exceptions are not returned as database detail. API model evaluation returns the stored held-out results from training; it does not generate fresh results or retrain. Configure administrator policy with validated weights (sum 1), ordered thresholds and bounded retry/time limits.
