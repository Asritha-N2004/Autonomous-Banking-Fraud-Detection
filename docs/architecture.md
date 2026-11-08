# Architecture

The framework uses an explicit typed state machine, the allowed local alternative to LangGraph. No chatbot API participates in scoring. Agent tools receive snapshots of authorized transaction data and can return structured evidence; they cannot issue SQL, call external services or execute banking actions.

```mermaid
flowchart LR
  UI[React / TypeScript dashboard] --> API[FastAPI + session / role checks]
  API --> DB[(SQLite / PostgreSQL)]
  API --> S[Executive supervisor]
  S --> P[Parallel specialist tools]
  P --> E[Evidence validation]
  E --> R[Risk and uncertainty]
  R --> I[Investigation / policy / report]
  I --> DB
  DB --> H[Authorized human review]
  H --> A[Audit and controlled evaluation records]
  P --> ML[Trusted calibrated model artifact]
  P --> G[Temporal heterogeneous graph]
```

Incoming events are validated and persisted, then explicitly analyzed via API or demo command. Core analysis is synchronous, with independent local tools in a thread pool. Supervisor checks every output against `AgentResult`, verifies referenced transaction IDs exist in the temporal snapshot and rejects missing provenance/uncertainty. Dependent stages receive only validated results. Missing specialists lower coverage/confidence and appear in policy checks; missing evidence or risk aborts the dependent flow. Every run has an overall deadline, retry bound and maximum attempts. Python native tool threads cannot be forcibly killed; hard process isolation is future work.

```mermaid
flowchart TD
  S[Executive supervisor: route and validate] --> T[Transaction]
  S --> B[Behavior]
  S --> A[Account]
  S --> G[Graph]
  S --> M[ML]
  S --> P[Pattern]
  T & B & A & G & M & P --> E[Evidence collection]
  E --> R[Risk assessment]
  R --> I[Investigation]
  I --> C[Compliance / policy]
  C --> F[Final reporting]
  F --> SR[Supervisor reference and completeness review]
  SR --> H[Human approval checkpoint]
```

Graph entities include accounts, synthetic customer ownership, transactions, beneficiaries, merchants and devices. A beneficiary account identifier in a simulator is treated as an observed destination identity, not independent proof of ownership. Verified shared identifiers and IP addresses are deliberately absent because the dataset does not provide authorization or verification. Each relationship carries transaction ID, source, amount and event timestamp. API graph snapshots are reconstructed from persisted transaction records; `build_graph.py` also persists entities/relationships for inspection. Graph is a derived view of relational evidence, not a second authoritative ledger.

```mermaid
stateDiagram-v2
  [*] --> Validated
  Validated --> ParallelAnalysis
  ParallelAnalysis --> Evidence
  Evidence --> Risk
  Risk --> Investigation
  Investigation --> Policy
  Policy --> Reporting
  Reporting --> AwaitingHumanReview
  AwaitingHumanReview --> InProgress: More information
  InProgress --> Closed: Authorized documented review
  AwaitingHumanReview --> Closed: Authorized documented review
  ParallelAnalysis --> Incomplete: Critical failure or timeout
```

There is no transition that moves money, restricts access or contacts an authority. Review records identity, timestamp, rationale, outcome, decision, policy and evidence IDs. Synthetic historical labels are immutable under review.

```mermaid
erDiagram
  ROLES ||--o{ USERS : permits
  USERS ||--o{ SESSIONS : authenticates
  CUSTOMERS ||--o{ ACCOUNTS : owns
  ACCOUNTS ||--o{ TRANSACTIONS : originates
  BENEFICIARIES ||--o{ TRANSACTIONS : receives
  MERCHANTS ||--o{ TRANSACTIONS : relates
  DEVICES ||--o{ TRANSACTIONS : observed
  TRANSACTIONS ||--o{ INVESTIGATIONS : investigates
  USERS ||--o{ INVESTIGATIONS : assigned
  INVESTIGATIONS ||--o{ EVIDENCE : contains
  INVESTIGATIONS ||--o{ INVESTIGATION_NOTES : records
  INVESTIGATIONS ||--o{ FRAUD_ALERTS : generates
  INVESTIGATIONS ||--o{ AGENT_RUNS : traces
  AGENT_RUNS ||--o{ AGENT_LOGS : captures
  TRANSACTIONS ||--o{ MODEL_PREDICTIONS : predicts
  MODEL_VERSIONS ||--o{ MODEL_METRICS : measures
  GRAPH_ENTITIES ||--o{ GRAPH_RELATIONSHIPS : links
```
