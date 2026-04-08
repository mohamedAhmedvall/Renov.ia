# Rapport EDA - Etat des lieux patrimonial

**Projet :** Prediction de casses de canalisations d'eau
**Date :** 2024
**Annee de reference :** 2024
**Phase :** 1 - Analyse exploratoire et etat des lieux

---

## 1. Perimetre des donnees

| Indicateur | Valeur |
|-----------|--------|
| Troncons total | 221,957 |
| Troncons EN SERVICE | 182,075 |
| Lineaire total EN SERVICE | 7,245.6 km |
| Anomalies retenues | 30,773 |
| Periode couverte | 1990 - 2024 |
| Dates de pose fiables | 91% |

**Filtre anomalies :** OBJET_DEPOSE_OU_ABANDONNE != 1 (garde 0=actif et -1=depose apres anomalie). Annee > 2024 exclue.

## 2. Profil patrimonial — Materiaux

| Materiau | Troncons | % troncons | Lineaire (km) | % lineaire | Age moyen |
|----------|---------|-----------|--------------|-----------|----------|
| FT | 97,354 | 53.5% | 3,782.2 km | 53.6% | 27 ans |
| FTG | 41,909 | 23.0% | 1,751.6 km | 24.8% | 64 ans |
| PEHD | 7,918 | 4.3% | 399.6 km | 5.7% | 17 ans |
| PVC | 3,643 | 2.0% | 282.6 km | 4.0% | 46 ans |
| POLY | 5,873 | 3.2% | 237.0 km | 3.4% | 48 ans |
| BTM | 2,067 | 1.1% | 156.2 km | 2.2% | 51 ans |
| ACIE | 1,413 | 0.8% | 151.1 km | 2.1% | 48 ans |
| FTVI | 12,123 | 6.7% | 112.1 km | 1.6% | 5 ans |
| AUTRE | 5,640 | 3.1% | 93.4 km | 1.3% | 35 ans |
| A.C | 320 | 0.2% | 34.7 km | 0.5% | 59 ans |

## 3. Anomalies

- 8,725 troncons EN SERVICE avec au moins 1 anomalie (4.8%)
- Moyenne : 757 anomalies/an
- Evenement rare → adapte au modele de survie

## 4. Chiffres cles

| Indicateur | Valeur |
|-----------|--------|
| Lineaire total | 7,245.6 km |
| 1% reglementaire minimum | 72.5 km/an |
| Age moyen du reseau | 35 ans |
| Troncons sinistres | 4.8% |

---
*Rapport genere automatiquement — Phase 1 (ref 2024)*
