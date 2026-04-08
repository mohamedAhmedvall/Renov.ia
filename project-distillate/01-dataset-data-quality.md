This section covers dataset scope, data quality, and target variable evolution. Part 1 of 4 from all project source files.

## Dataset Scope & Composition

- Total troncons: 221,957; EN SERVICE 182,075 (82%); ABANDONNE 29,547 (13%); DEPOSE 9,457 (4%)
- EN SERVICE lineaire: 7,245.6 km; regulatory min 1% = 72.5 km/year
- Anomalies retained after cleaning: 30,773

## Material Breakdown & Age

- Fonte (FT + FTG combined dominant; FT 97,354 @ 27yr avg; FTG 41,909 @ 64yr avg); 76.5% of network
- PEHD 7,918 (4.3%) @ 17yr; PVC 3,643 (2%) @ 46yr; Amiante_ciment, Acier, Beton, Autre comprise remainder
- Network average age: 35yr; FTG oldest (64yr age-driven renewals); younger materials (PEHD 17yr) mixed with post-1980s installations

## Target Variable Evolution V1→V4

- V1: Binary anomaly flag (not true target; confused event vs state)
- V2: ABANDONNE/DEPOSE vs EN SERVICE; all included; age at event date to prevent temporal leakage
- V3: ABANDONNE only; DEPOSE excluded (median 20yr age, 60% <30yr, Bon state suggests chantier-driven unpredictability); DEPOSE kept as label=0 negatives
- V4 (FINAL): ABANDONNE vs EN SERVICE; DEPOSE entirely excluded from dataset

## Data Quality Issues & Fixes V1→V4

- Dates=1900 (SIG placeholders); 17k troncons marked unreliable; age imputed by famille_mat median; future dates excluded (1 @ 2033); V2 switched age calc to event date (avoids temporal leakage)
- Anomalies: Flag=1 (abandoned at anomaly time) excluded; Flag=0 (active) and Flag=-1 (abandoned after) kept; temporal scope V2+ counts anomalies BEFORE event date; 1503 orphaned (GID_OBJET absent from cana) excluded V3
- ETAT: 16 raw values → 4 normalized (Bon, Moyen, Mauvais [merged Vetuste/Sature/FUITES_MULTIPLES], Inconnu); V4 fix mapped Inconnu to NaN not 0
- DIAMETRE & LONGUEUR: Zero = NaN; V3+ imputed DIAMETRE by famille_mat median + global fallback; LONGUEUR by global median
- MATERIAU: 29 raw → 8 families (Fonte, Fonte_grise, Plastique [PVC/PEHD/PEBD/POLY], Amiante_ciment, Acier [FER/GALV/INOX/ACIE/AFCO], Beton [BTM/BA/CENT], Autre)

## Critical Finding: 89.6% Abandonments Have Zero Anomalies

- ABANDONNE: 10.2% with anomalies; DEPOSE: 25.5% with anomalies
- Single fuite often triggers abandonment (economic decision, not advanced degradation)
- Limits anomaly count as predictive signal

## Data Quality Constraints

- TERRAIN, PROFONDEUR, PRESSION, QUALITE_GEOMETRIE <60% filled; excluded from feature set
- Some EN SERVICE records have ABANDON date filled (data corruption); not fully resolved
- DIAMETRE/LONGUEUR missing rates not quantified; median imputation assumes MCAR (not validated)
- Age imputation by famille_mat: not cross-validated by material group
