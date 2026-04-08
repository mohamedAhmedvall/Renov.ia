---
type: bmad-distillate
sources:
  - "../scripts/data_cleaning.py"
  - "../scripts/data_cleaning_v2.py"
  - "../scripts/data_cleaning_v3.py"
  - "../scripts/data_cleaning_v4.py"
  - "../scripts/eda_phase1.py"
  - "../scripts/phase2_model.py"
  - "../scripts/phase2_model_v4.py"
  - "../scripts/phase2_model_v5.py"
  - "../scripts/phase2_model_v6.py"
  - "../scripts/phase2_model_v7.py"
  - "../scripts/_audit_dataset.py"
  - "../scripts/_explore_fdv.py"
  - "../scripts/analyse_anomalies_fdv.py"
  - "../scripts/_mlflow_log_v5.py"
  - "../output/rapport_eda_phase1.md"
downstream_consumer: "next model iteration V8"
created: "2026-04-03"
token_estimate: 7200
parts: 5
---

## V8 Context: 7-Iteration Evolution from Data Cleaning through Production Scoring

- Distillate of 15 source files (52K tokens) across data cleaning (V1-V4), modeling pipeline (V3-V7), and exploratory analysis
- Downstream consumer: V8 model iteration for water pipe failure prediction (predire casse/fin de vie des canalisations)
- Split into 4 sections covering dataset, features, model results, and V8 roadmap
- V7 is current production baseline: AUC=0.8395, +0.1332 vs age-only, backtesting AUC=0.8413±0.0127

## Section Manifest

- [01-dataset-data-quality.md](01-dataset-data-quality.md) — Scope, material composition, target evolution V1→V4, data issues, critical finding (89% no anomalies)
- [02-feature-engineering.md](02-feature-engineering.md) — V1→V4 feature iterations, ablation, final 8-feature set, APIs, constraints
- [03-model-results-validation.md](03-model-results-validation.md) — Modeling evolution V3-V7, hyperparameters, metrics, backtesting, SHAP, scoring pipeline
- [04-v8-roadmap.md](04-v8-roadmap.md) — Current limitations, open questions, improvement ideas, success criteria

## Cross-Cutting Constraints

- ANNEE_REF=2024 hardcoded throughout; temporal leakage fixed V2+
- 17% troncons (17k) have unreliable pose dates; mitigated via famille_mat median imputation
- ~90% of abandonments have zero anomalies; anomaly count only weak predictor
- Small test positive set → wide confidence intervals; backtesting AUC std~0.01-0.03
- TE smoothing=10 fixed V4+; no sensitivity analysis documented
- DIAMETRE/LONGUEUR & age imputation assume MCAR; not validated

## Evolution Pattern

- V1→V2: temporal leakage fix (event date age)
- V2→V3: target narrowing (ABANDONNE only); feature noise removal
- V3→V4: DEPOSE exclusion; age imputation flag
- V5→V7: TE pipeline fixes (P0), anom feature pruning (P1), data quality hardening (P2), final validation
- V7 performance stable: AUC=0.8395, +0.1332 vs age baseline, backtesting robust (±0.0127)
