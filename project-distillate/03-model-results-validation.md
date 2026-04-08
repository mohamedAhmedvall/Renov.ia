This section covers modeling evolution, hyperparameters, metrics, backtesting, SHAP, and scoring pipeline. Part 3 of 4 from all project source files.

## Modeling Evolution V3→V7

- V3: 4-model baseline (Logistic, RF, XGBoost, HistGradientBoosting); target=anomaly flag; SMOTE 10%; cascade classification→survival
- V4: Target pivot to ABANDONNE/DEPOSE; age corrected; discovery 90% abandonments zero anomalies; 6 backtesting windows
- V5: XGBoost only; fixed hyperparameters; error analysis; cascade Cox PH
- V6: Target=ABANDONNE only; age-based baseline (AUC=0.7143); 12 features
- V7 (FINAL): TE train-only pipeline fix (P0); anomaly features 5→1 (P1); 3 backtesting windows, DEPOSE excluded, age_imputed flag (P2)

## Hyperparameters

- V3-V4 HPO: RandomizedSearchCV; RF 20 iter, XGBoost 30 iter, HistGradientBoosting 20 iter; 3-fold CV
- V5-V7 Fixed: n_estimators=500; max_depth=7-8; learning_rate=0.03; subsample=0.8; colsample_bytree=0.7-0.8; scale_pos_weight=n_neg/n_pos (V5=15.3)

## Validation Strategy

- Train/Test: V3-V6 used 75/25 stratified split (random_state=42)
- Backtesting: V4 tested 6 temporal windows; V7 refined to 3 windows (2012-2016, 2014-2018, 2016-2020) with split_year=2018

## Key Metrics Across Versions

- V5: AUC=0.8485; AP=0.3092; F1=0.3605; Capture@20%=68.5%; scale_pos_weight=15.3
- V6: AUC=0.8358; AP=0.2230; Baseline age AUC=0.7143; Model gain=+0.1215; Capture@20%=65.8%
- V7 Hold-out Test: AUC=0.8395; AP=0.2544; Baseline age AUC=0.7063; Model gain=+0.1332; Capture@20%=66.5%
- V7 Backtesting (3 windows): AUC=0.8413±0.0127 (std robust); temporal stability confirmed

## V7 Feature Ablation (Impact on Test AUC)

- Longueur: Δ=+0.0260 (strongest); Age: Δ=+0.0221; Diametre: Δ=+0.0166; Famille_materiau: Δ=+0.0076; Etat: Δ=+0.0021; Nb_fuites: Δ=+0.0011; Decennie_pose: Δ=+0.0006; Age_imputed: Δ≈0.0000
- All features contribute positively; none harmful in final set

## V7 SHAP Feature Importance (Mean Absolute)

- Age: 0.7089 (dominant driver); Longueur: 0.5763; Age_imputed: 0.4375; Decennie_pose: 0.3305; Diametre: 0.2045; Famille_materiau: 0.1702; Nb_fuites: 0.0606; Etat: 0.0443

## Scoring Pipeline (Production)

- Population: 182,075 EN SERVICE troncons; TE mapping saved to JSON external dict
- Pipeline: Impute(median) → build_features_v4(te_map=...) → predict_proba → SCORE/RANG/TOP_PCT
- V7 top 10% (18,298 troncons): mean score 0.795; mean age 57yr; Fonte_grise dominant (50%); Fonte secondary (30%)

## Cascade & Survival Exploration (V5)

- Classification model 70% weight + Cox PH on top 30% candidates
- AUC improvement ~0.01-0.02 vs classification alone (marginal; not pursued V6+)
- Kaplan-Meier by material: Fonte_grise ~113yr; Fonte ~68yr; Acier ~68yr; Plastique ~73yr (survival curves show family-level trends)

## MLflow Logging

- tracking_uri=file:///mlruns; one experiment per version
- Captures: params, metrics, SHAP plots, ablation CSVs, scoring outputs, model artifacts
- Enables full reproducibility and cross-version comparison
