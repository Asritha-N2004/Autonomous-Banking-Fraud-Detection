# Methodology

Default generator uses seed 42, 70 origin accounts, 80 destination identifiers, overlapping lognormal amount distributions, categorical transaction/channel values, and injected beneficiary/device shifts. Labels simulate outcomes. This is deliberately a controlled benchmark and lacks many confounders of real banking.

Features: log amount, hour/day, prior account count and mean, amount/mean ratio, strictly prior 24h velocity, distinct counterparties, new beneficiary/device and account graph degree. Equal timestamp events share one past snapshot. No historical label or future human outcome enters the feature matrix. Features may use earlier unlabeled observations from validation/test periods, reflecting online history updates; fitted preprocessing uses training records only.

After chronological ordering, train/calibration/test proportions are 60/20/20 with equal-time groups kept together. Median imputation and standardization fit only training records; one-hot encoding ignores unseen categories. Logistic regression and random forest use class balancing. Gradient boosting is a conventional comparison; optional XGBoost uses positive-class weighting. Sigmoid calibration uses validation only. Test metrics include PR-AUC, ROC-AUC, precision, recall, F1, false positive/negative rates, top 5% precision/recall and confusion matrix. The classification threshold is .5, a research setting rather than an optimized operational policy.

Isolation Forest and novelty Local Outlier Factor fit training features without labels. Ranking metrics use raw anomaly scores. The API reports Isolation Forest training-reference percentile separately from calibrated probability; a percentile is not the probability of fraud. Autoencoder fits training records labeled normal and reports reconstruction-error ranking. GraphSAGE is a separate transaction-node temporal experiment with account/device predecessor edges, forward-only message passing, training-only labels and validation-logit calibration.

API explanation replaces one transformed feature at a time with a training-reference median, then measures change in predicted probability. This is local sensitivity, not an additive or causal attribution. One-hot replacement can create off-manifold combinations; interpret cautiously.

## Priority framework

Initial weights: transaction .16, behavioral .18, account .12, graph .16, ML .28, verified pattern .10. Priority = 100 × sum(weight × indicator). Configured thresholds: medium 30, high 55, critical 75. These arbitrary research weights are not a validated fraud probability or universal banking standard. Each component and weighted contribution is reported. Absent signals contribute zero without renormalization; their absence increases uncertainty. Score divergence greater than .55 raises a contradiction flag. Confidence is mean available tool quality; it is a heuristic, not a confidence interval.

Graph methods include directed transfer projection, degree, sampled betweenness (up to 40 account nodes, seed 42), PageRank, greedy modularity communities, connected components and temporal neighborhoods. Shared-device counts and reciprocal links are explainable heuristic leads. They do not establish collusion.

The experiment runner compares baseline ML, ML+graph, full workflow and five ablations. Evidence counts, latency and incomplete runs are measured. Human workload and investigation correctness require separate blinded studies; no simulated number is substituted for those outcomes. Channel subgroups are reported where available; protected attributes are deliberately absent, so protected-group fairness cannot be assessed here.
