This section covers feature engineering evolution, ablation findings, and production APIs. Part 2 of 4 from all project source files.

## Feature Engineering Evolution V1→V4

- V1 (Baseline): 11 features — age, etat_ord, diametre, longueur, famille_materiau, decennie_pose, nb_anomalies, nb_fuites, a_casse, temps_depuis_derniere_anomalie, intervalle_moyen_ans, densite_anomalies_ml
- V2→V3 (Expansion & Refinement): V2 added age², log_age, age_x_materiau, LabelEncoder(famille), fuites_par_an_age, densite_anom_ml, densite_fuites_ml, acceleration (20 features); V3 removed age², log_age, intervalle_moyen (noise); swapped LabelEncoder(FAMILLE) → Target Encoding; densite_anom_ml → densite_fuites_km; removed acceleration, fuites_par_an_age; cut to 12 features
- V4 (Final Reduction & Production Fixes): P0 removed Target Encoding from pipeline (moved to model, external te_map, train-only); P1 reduced anomaly features (removed: nb_anom, a_deja_fuite, densite_fuites_km, age_x_famille, temps_depuis_dern_fuite; kept: nb_fuites only); P2 DEPOSE excluded, age_imputed flag added, ETAT Inconnu=NaN; final set: 8 features

## Final Feature Set (V4→V7)

- age; age_imputed (flag); diametre; longueur; etat_ord (4 categories); decennie_pose; famille_enc (target-encoded, external map); nb_fuites

## Ablation Findings V1→V4

- Harmful: age² (polynomial overfitting); log_age (noise); famille_mat as LabelEncoded (leakage risk)
- Redundant: intervalle_moyen; acceleration; a_deja_fuite; nb_anom (subsumed by nb_fuites)
- Weak: densite_fuites_km; temps_depuis_derniere_fuite; fuites_par_an_age; age_x_famille
- Robust: age, nb_fuites, etat_ord, diametre, longueur, decennie_pose, famille_enc (all positive contribution)

## API & Production Functions

- load_and_clean_v4(data_dir): Loads canalisation + anomalies CSVs; outputs cana, anom_clean (cleaned, deduplicated, date-fixed)
- build_features_v4(cana, anom_clean, cutoff_year=None, te_map=None): If cutoff_year provided: train mode (temporal split); if te_map provided: applies external encoding; outputs df, feature_cols, feature_names
- compute_target_encoding(df, col='famille_mat', target='y', smoothing=10): Bayesian smoothing TE on TRAIN set only; outputs dict {category: value, "__global__": mean}; smoothing=10 fixed, untested for sensitivity

## Feature Engineering Constraints

- Target Encoding smoothing=10 hardcoded; no sensitivity analysis
- Age imputation by famille_mat median: assumes grouping meaningful, not cross-validated
- Anomaly features heavily pruned: nb_fuites only signal (90% no anomalies in abandonments limits utility)
- Decennie_pose contributes weakly despite decades of data; possibly proxy for material drift
