# Datasets

## Bundled development source

Source: `backend/app/ml/data.py` (original project generator). Generated locally, seed 42; no real customer records. The project MIT license applies to original source and generated sample records. Generation date is recorded by local artifacts/commands; the reference event epoch is **2025-01-01 UTC**, not a retrieval date. The generator is not PaySim or BankSim.

Canonical fields: `id`, `account_id`, `beneficiary_id`, optional `merchant_id` / `device_id`, timezone-aware `timestamp`, positive finite `amount`, ISO-style three-letter `currency`, transaction type (`transfer`, `purchase`, `withdrawal`, `deposit`), channel (`mobile`, `web`, `atm`, `branch`), `synthetic`, optional historical label 0/1 and `source`. Unique IDs and referential records are enforced. Labels are simulated, not adjudicated findings. No names, addresses, protected attributes or IP addresses are generated.

## Optional user-supplied public sources

Public records were not downloaded or benchmarked. Source links checked 2026-11-08. Users must record their own retrieval date, file hash, license and approval when importing. Simulator source licensing must not be confused with dataset distribution licensing.

| Source | Route | Access/license status and limitations |
|---|---|---|
| [PaySim author repository](https://github.com/EdgarLopezPhD/PaySim) / [dataset distribution](https://www.kaggle.com/datasets/ealaxi/paysim1) | `--kind paysim` CSV adapter | Author repository describes the mobile money simulator and links its dataset. Repository GPL-3.0 applies to simulator code; verify the dataset's own distribution terms before use. No simulator code is copied here. |
| [BankSim dataset distribution](https://www.kaggle.com/datasets/ealaxi/banksim1) | `--kind banksim` CSV adapter | User supplies authorized CSV; license/access terms not verified locally. Adapter ignores age/gender/location features and never uses them as risk indicators. |
| [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) | Standalone offline research only; no graph adapter | No verified customer/account graph identity is supplied to this implementation. Do not invent identities or connect unrelated card records. Check source terms. |
| [IEEE-CIS competition](https://www.kaggle.com/competitions/ieee-fraud-detection) | Not integrated | Competition account/rule acceptance may be required; no access is assumed and no record was retrieved. |

PaySim `step` becomes hours after the arbitrary 2025-01-01 UTC reference; BankSim `step` becomes days. These are derived simulation times, not real timestamps. PaySim/BankSim currency is `XXX` (unspecified), avoiding an invented monetary unit. The local generated dataset uses INR; user-supplied canonical records must declare their actual unit. Adapters preserve only real source account/merchant identifiers; missing device identities stay missing. Graph customer ownership nodes in the local schema are synthetic grouping identifiers, not verified KYC facts.

The canonical adapter validates all fields and supports user-declared synthetic data. Data ingestion is atomic and rejects duplicates. Missing numeric model values are imputed by the fitted training pipeline; invalid transaction amounts/times are rejected rather than silently repaired. Split records by time and use approved labels for controlled evaluation. Never upload sensitive banking data to third-party services.
