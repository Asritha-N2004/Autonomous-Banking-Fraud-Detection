# Actual model evaluation

Recorded from executed local runs on 2026-11-08. All records are synthetic; none of these results validate banking deployment.

Baseline artifact: `baseline-10b78d7a1569`. Dataset SHA-256: `c6531c4a7f878dee89fb72b42933dda7b4a73880b368bb189d5e285052964bf0`.

Temporal split: 1440 train / 480 calibration / 480 test. Test positives: 20 / 480. Training positive rate: 0.0618.

| Model | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| logistic_regression | 0.9267 | 0.9897 | 1.0000 | 0.8000 | 0.8889 |
| random_forest | 0.9673 | 0.9983 | 1.0000 | 0.8000 | 0.8889 |
| gradient_boosting | 0.9405 | 0.9958 | 1.0000 | 0.8000 | 0.8889 |
| xgboost | 0.8695 | 0.9820 | 1.0000 | 0.8000 | 0.8889 |
| isolation_forest | 0.6935 | 0.9784 | ranking only | ranking only | ranking only |
| local_outlier_factor | 0.0778 | 0.5424 | ranking only | ranking only | ranking only |
| autoencoder | 0.3477 | 0.9238 | ranking only | ranking only | ranking only |
| graphsage | 1.0000 | 1.0000 | 0.9524 | 1.0000 | 0.9756 |

Random forest confusion matrix: `[[460, 0], [4, 16]]`; precision@24 .7500, recall@24 .9000; false-positive rate .0000, false-negative rate .2000. Classification threshold .5. Anomaly models use ranking metrics only.

## Runtime and reproducibility

Core libraries: `{"joblib": "1.4.2", "networkx": "3.4.2", "numpy": "2.2.5", "pandas": "2.2.3", "scikit-learn": "1.6.1"}`.
Advanced run: `{"torch": "2.13.0+cpu", "torch_geometric": "2.6.1"}`; seed 42, 35 epochs. Optional requirements name PyTorch 2.7.0 as a portable installation target; the available local runtime tested here was 2.13.0+cpu with PyG 2.6.1. That exact optional pin has not been separately installed/tested.

An initial preinstalled-library run gave a different forest ranking (PR-AUC 1.0). The pinned-core rerun above supersedes that exploratory result. Environment/version metadata is part of the artifact identity. No result was replaced with a fabricated target metric.

## Operational and ablation experiment

Fixed-seed random sample of 60 later test records, including 4 positives. Sampling uses no labels. Timing includes local tool execution and is hardware/load dependent. Priority scores retain original weights; a .5 cutoff is a research comparison, not an operationally tuned decision.

| Variant | PR-AUC | Mean duration ms | Mean evidence items | Incomplete / 60 |
|---|---:|---:|---:|---:|
| single_model | 1.0000 | 112.8 | 0.0 | 0 |
| ml_plus_graph | 1.0000 | 348.1 | 2.0 | 0 |
| full | 1.0000 | 303.2 | 6.0 | 0 |
| without_behavioral | 1.0000 | 310.1 | 5.0 | 0 |
| without_graph | 1.0000 | 121.8 | 5.0 | 0 |
| without_ml | 0.8750 | 166.8 | 5.0 | 0 |
| without_evidence | 1.0000 | 364.1 | 0.0 | 60 |
| without_supervisor_aggregation | 0.0667 | 249.7 | 6.0 | 60 |

The full workflow produced six specialist evidence items per completed case, versus two with ML+graph alone. These counts measure coverage, not correctness. Removing evidence or aggregation intentionally makes the workflow incomplete. A high ranking in an incomplete ablation does not constitute a usable investigation. The no-supervisor variant represents omission of the aggregation stage, not removal of every safety check.

No investigator workload study was run. No multi-seed confidence interval, external dataset evaluation, real-world false-positive estimate or protected-group fairness claim is supported. Operational channel subgroup metrics are in the baseline JSON; small subgroup positive counts make them unstable.

## Reproduction

```powershell
python scripts/generate_synthetic_data.py --rows 2400 --seed 42
python scripts/train_models.py
python scripts/evaluate_models.py
python scripts/train_advanced.py --epochs 35
python scripts/experiments.py --count 60
```

The baseline evaluation endpoint returns these stored held-out metrics rather than rerunning model training. Models are withheld for historical events at or before the calibration cutoff to prevent hindsight scoring.
