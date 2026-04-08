This section covers current limitations, open questions, improvement ideas, and success criteria. Part 4 of 4 from all project source files.

## Current V7 Limitations

- False negative rate: 20-30% irreducible in backtests; young pipes abandoned for economic not degradation-driven reasons
- Test positive set size: n~3k (1.7% of EN SERVICE); wide confidence intervals on minority class metrics
- Temporal drift observed: AUC varies by backtesting window (std~0.01-0.03); some cohorts more predictable than others
- Anomaly feature severely pruned: nb_fuites weak signal; 90% no-anomaly abandonments limit usefulness
- Smoothing factor (TE smoothing=10): fixed since V4; sensitivity untested

## Open Questions for V8

- Is age degradation truly linear or segmented by material? Should log_age be reconsidered with different materials?
- Why is densite_fuites_km not predictive despite intuitive appeal?
- Can age imputation by famille_mat be validated cross-material?
- Missing rates (DIAMETRE, LONGUEUR) not quantified; median imputation validity not tested
- Are TERRAIN, PROFONDEUR, PRESSION, QUALITE_GEOMETRIE worth engineering if backfilled?
- EN SERVICE records with ABANDON dates: data corruption scope?
- Can temporal model (survival/time-to-event) reduce FN rate on young pipes?
- Would ensemble stacking improve robustness?
- Can calibration (Platt scaling) improve confidence intervals?
- Does TE smoothing=10 need tuning?

## Improvement Ideas for V8

- New Features: water chemistry or pressure proxies (if PRESSION backfillable); recency of pipe installation (interact with material); chantier activity density (proxy for economic renewal cycle); failure rate by lateral (neighborhood effect)
- Modeling: time-to-event (survival regression + competing risks for chantier); ensemble (stack XGB + LightGBM + logistic calibrator); temporal cross-validation (rolling window, not random); confidence intervals via Platt scaling or isotonic regression
- Data & Validation: quantify DIAMETRE/LONGUEUR missing rates by material; test log_age interaction with material; validate age imputation stability; investigate EN SERVICE + ABANDON date corruption scope; consider material-stratified backtesting
- Baseline: age-based model (AUC~0.71) strong; V7 gain=+0.13 significant; compare V8 against V7 (not age) for incremental validation

## V8 Success Criteria

- Backtesting AUC ≥0.8450 (consistent across windows, std <0.015)
- Capture@20% ≥67% (top 20% of EN SERVICE captures ≥67% of true abandonments)
- FN analysis: reduce under-30yr FN rate or stratify confidence by age group
- Production readiness: TE mapping, imputation strategy, feature API stable; MLflow logs all decisions
