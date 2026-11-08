# Security and governance

This local research stack has meaningful controls but is not a production security certification.

Local self-registration creates only Analyst accounts. It requires a valid unique username and matching passwords of at least 12 characters, salts/hashes passwords, sets the usual expiring HTTP-only session and records a self-registration audit event. Role fields are rejected. Registration shares the login rate limit. An administrator must bootstrap the workspace before registration is available; higher privileges use the existing administrator-only user creation endpoint. Invite-only onboarding and external identity verification remain production integration work.

Passwords use salted scrypt; only hashes are stored. Bootstrap requires a user-provided long password; no default account password is embedded in source. Session tokens have high entropy, SHA-256 hashes at rest, expiry, HTTP-only/same-site cookies and logout revocation. `COOKIE_SECURE=true` is required behind HTTPS. Login and API limits are in-process and reset on restart; multi-worker use needs a shared gateway. CORS uses explicit origins and cookie writes reject foreign origins. SQLAlchemy binds values; imported text is data and cannot invoke tools or SQL.

| Role | Access |
|---|---|
| ADMIN | User/configuration/model administration, all investigations and exports |
| SUPERVISOR | Transactions and analytics, case assignment/review/closure, permitted exports |
| FRAUD_INVESTIGATOR | Assigned cases, evidence, notes, investigation initiation and own traces; no global transaction browser or configuration |
| ANALYST | Approved global transaction/model/aggregate analytics; no evidence, case detail or exports |
| AUDITOR | Read-only global transactions/cases/evidence/traces/audit; no writes or exports |

Case closure/outcome recording requires supervisor/admin role, rationale, reviewer identity, evidence references, policy version and timestamp. Assignment changes require supervisor/admin. There is no banking action adapter or external reporting capability. Approving a recommendation records review only. Human outcomes never overwrite original benchmark labels, and no model automatically retrains itself from its own predictions.

Data minimization: synthetic IDs, no protected demographic fields, no IP collection. Historical training labels and present model predictions are separately persisted. Pattern retrieval requires an earlier human-confirmed closed case whose review timestamp predates the event. Logs are accessible by role; investigators cannot inspect other investigators' traces. Reports require permitted case access; HTML/XML is escaped in PDF and formula-leading CSV fields are neutralized.

Audit entries accompany authentication, ingestion, analysis, notes, assignment/status/review, settings, user creation, training and exports. Audit tables are append-only through exposed APIs but not tamper-proof against database administrators. Production needs external immutable audit storage, retention/legal-hold enforcement, backups, key management, encryption at rest, SSO/MFA, network isolation, security testing, dependency scanning and incident response.

Retention settings are stored and exposed to reports; automated purge and legal holds are not implemented. No deletion endpoint is provided. Migrations bootstrap initial schema and must be extended explicitly for upgrades. Trusted model files use Python serialization and must never originate from untrusted uploads. Run only local trusted artifacts. An investigation timeout rejects late results but does not kill native worker threads; production should isolate tools in killable worker processes. Heavy train/graph routes need job queues and quotas before multi-user production use. No claim of regulatory compliance is made by policy checks.
