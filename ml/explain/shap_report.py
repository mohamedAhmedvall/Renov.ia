"""Explicabilité SHAP — importance globale des features du modèle Poisson.

L'explicabilité n'est pas un luxe ici : la priorisation engage des budgets
publics, le gestionnaire doit pouvoir justifier POURQUOI un tronçon est
prioritaire (âge ? matériau ? antécédents ?). SHAP (TreeExplainer, exact sur
les arbres) fournit l'attribution locale par tronçon et, agrégée en moyenne
absolue, l'importance globale.
"""

import pandas as pd
import shap


def shap_importance(model: dict, X: pd.DataFrame, max_rows: int = 2000) -> pd.DataFrame:
    """Importance globale = moyenne des |valeurs SHAP| par feature (ordre décroissant)."""
    sample = X.sample(n=min(max_rows, len(X)), random_state=0) if len(X) > max_rows else X
    explainer = shap.TreeExplainer(model["booster"])
    values = explainer.shap_values(sample)
    imp = pd.DataFrame(
        {"feature": sample.columns, "importance": abs(pd.DataFrame(values)).mean(axis=0).to_numpy()}
    )
    return imp.sort_values("importance", ascending=False).reset_index(drop=True)
