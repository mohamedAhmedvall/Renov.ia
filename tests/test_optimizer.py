"""Tests pour le module optimizer."""

import pandas as pd
import pytest

from optimizer import optimize_renewal


class TestOptimizeRenewal:
    def test_basic_optimization(self, sample_scoring_df, sample_config, sample_referentiel_df):
        params = {
            "budget": 500_000,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        assert result["success"] is True
        assert result["kpis"]["budget_utilise"] <= 500_000
        assert result["kpis"]["nb_troncons"] > 0
        assert len(result["troncons_selectionnes"]) > 0

    def test_zero_budget_fails(self, sample_scoring_df, sample_config, sample_referentiel_df):
        params = {
            "budget": 1,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        # Avec un budget de 1€, on ne peut rien sélectionner (sauf si contrainte 1% active)
        if result["success"]:
            assert result["kpis"]["budget_utilise"] <= 1

    def test_forced_troncons(self, sample_scoring_df, sample_config, sample_referentiel_df):
        forced = {str(sample_scoring_df["OBJET"].iloc[0])}
        params = {
            "budget": 5_000_000,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
            "troncons_forces": forced,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        assert result["success"] is True
        selected_ids = result["troncons_selectionnes"]["OBJET"].astype(str).tolist()
        assert list(forced)[0] in selected_ids

    def test_excluded_troncons(self, sample_scoring_df, sample_config, sample_referentiel_df):
        excluded = set(sample_scoring_df["OBJET"].astype(str).tolist()[:5])
        params = {
            "budget": 5_000_000,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
            "troncons_exclus": excluded,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        assert result["success"] is True
        selected_ids = set(result["troncons_selectionnes"]["OBJET"].astype(str).tolist())
        assert selected_ids.isdisjoint(excluded)

    def test_fuites_evitees_uses_backtesting(self, sample_scoring_df, sample_config, sample_referentiel_df, sample_backtesting_df):
        params = {
            "budget": 5_000_000,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
            "df_backtesting": sample_backtesting_df,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        assert result["success"] is True
        # Le taux de capture moyen du backtesting est ~75%, pas 0.3
        assert result["kpis"]["fuites_evitees"] > 0

    def test_contrainte_1pct(self, sample_scoring_df, sample_config, sample_referentiel_df):
        params = {
            "budget": 5_000_000,
            "horizon": 3,
            "type_chantier": "urbain_standard",
            "materiau_remplacement": "fonte_ductile",
            "df_referentiel": sample_referentiel_df,
            "contrainte_1pct": True,
        }
        result = optimize_renewal(sample_scoring_df, sample_config, params)
        assert result["success"] is True
        km_total = sample_config["km_total_reseau"]
        km_renew = result["kpis"]["km_renouveles"]
        assert km_renew >= km_total * 0.01  # au moins 1%

    def test_empty_df(self, sample_config):
        df_empty = pd.DataFrame(columns=["OBJET", "score_h3", "DIAMETRE", "age"])
        params = {"budget": 500_000, "horizon": 3}
        result = optimize_renewal(df_empty, sample_config, params)
        assert result["success"] is False
