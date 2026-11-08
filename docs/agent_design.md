# Agent contracts and dependencies

All specialist outputs contain agent name, normalized indicator score, confidence, findings, transaction references, provenance, uncertainty and typed details. Scores are not interchangeable probabilities. Agents consume one transaction, strictly earlier history, features, configured policy and earlier human-confirmed cases. They have no write-capable tools.

| Agent | Inputs/tools | Output and method | Dependency |
|---|---|---|---|
| Transaction monitoring | Transaction and rolling features | Amount/mean ratio and 24h velocity indicator | Snapshot |
| Behavioral | Past account history | Statistical z-score, new-device signal, insufficient-history warning | Snapshot |
| Account intelligence | Incoming/outgoing records | Flow totals, counterparties, beneficiary novelty | Snapshot |
| Graph intelligence | NetworkX temporal snapshot | Shared-device records, reciprocal links, centrality, community and relationship references | Snapshot |
| ML detection | Trusted model and engineered features | Calibrated probability, Isolation Forest percentile, local replacement sensitivities, version | Snapshot + trained artifact |
| Pattern recognition | Earlier closed human-confirmed cases | Account/beneficiary match leads with source transaction IDs | Prior review outcomes only |
| Evidence collection | Validated specialist results | Chronological evidence items, quality, sources, missing specialists | Six parallel tools |
| Risk assessment | Scores and configurable weights | Priority, breakdown, confidence, missing-signal uncertainty and disagreement | Evidence + specialists |
| Investigation | Evidence and risk | Timeline, questions, missing information and recommendations | Evidence/risk |
| Compliance/policy | Coverage, policy and investigation | Human-review requirement, missing documentation and policy version | Investigation |
| Final reporting | All accepted outputs | Structured report, limitations and executive summary | Compliance |

Supervisor routing conditionally omits tools in experiments, retries failed or invalid tool results, rejects unknown references, and aborts downstream work if core evidence or risk cannot be produced. All other partial coverage is disclosed and escalated to human review. Logs store timing, attempts, input summaries, output and errors. The supervisor always routes completed reports to human review, even at low priority; medium/high/critical categories additionally appear as alerts according to configured thresholds.

Pattern matching deliberately does not use simulated labels as confirmed cases. This conservative method is not a learned fraud typology recognizer. Graph shared-device observations are unverified relationships and are never called proof. Distinct specialists live in one module to keep the research implementation reviewable; each is independently callable and tested through the supervisor.
