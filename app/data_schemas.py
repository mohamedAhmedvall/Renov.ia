"""Schémas de données pour la validation des fichiers CSV d'entrée."""

# Colonnes requises pour le fichier scoring
SCORING_REQUIRED_COLUMNS = [
    "OBJET",
    "MATERIAU",
    "DIAMETRE",
    "famille_mat",
    "age",
    "score_h1",
    "score_h3",
    "score_h5",
    "rang",
    "top_pct",
]

# Types attendus pour le casting avec coerce
SCORING_DTYPES = {
    "OBJET": "str",
    "MATERIAU": "str",
    "DIAMETRE": "float",
    "famille_mat": "str",
    "age": "float",
    "score_h1": "float",
    "score_h3": "float",
    "score_h5": "float",
    "rang": "int",
    "top_pct": "float",
}

# Colonnes requises pour le fichier référentiel
REFERENTIEL_REQUIRED_COLUMNS = [
    "OBJET",
    "STATUT_OBJET",
    "MATERIAU",
    "DIAMETRE",
    "LONGUEUR",
    "POSE",
]

# Types attendus pour le référentiel
REFERENTIEL_DTYPES = {
    "OBJET": "str",
    "STATUT_OBJET": "str",
    "MATERIAU": "str",
    "DIAMETRE": "float",
    "LONGUEUR": "float",
    "POSE": "str",
    "ETAT": "str",
    "TERRAIN": "str",
    "PROFONDEUR": "float",
}

# Champs clés pour le calcul ICP (Indice de Connaissance Patrimoniale)
ICP_FIELDS = [
    "MATERIAU",
    "DIAMETRE",
    "LONGUEUR",
    "POSE",
    "age",
]

# Colonnes requises pour SHAP importance
SHAP_REQUIRED_COLUMNS = [
    "feature",
    "mean_abs_shap",
]

# Colonnes requises pour backtesting
BACKTESTING_REQUIRED_COLUMNS = [
    "window",
    "auc",
    "capture_top20",
]
