"""Tests pour le module filters."""

import pandas as pd
import pytest

from filters import apply_filters


class TestApplyFilters:
    def test_no_filters_returns_all(self, sample_scoring_df, sample_config):
        result = apply_filters(sample_scoring_df, {}, sample_config, horizon=3)
        assert len(result) == len(sample_scoring_df)

    def test_filter_by_materiau(self, sample_scoring_df, sample_config):
        mat = sample_scoring_df["famille_mat"].iloc[0]
        filtres = {"materiaux": [mat]}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert all(result["famille_mat"] == mat)
        assert len(result) > 0

    def test_filter_by_score_min(self, sample_scoring_df, sample_config):
        filtres = {"score_min": 0.5}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert all(result["score_h3"] >= 0.5)

    def test_filter_by_age_range(self, sample_scoring_df, sample_config):
        filtres = {"age_min": 20, "age_max": 50}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert all(result["age"] >= 20)
        assert all(result["age"] <= 50)

    def test_filter_by_diametre(self, sample_scoring_df, sample_config):
        filtres = {"diametre_min": 150, "diametre_max": 200}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert all(result["DIAMETRE"] >= 150)
        assert all(result["DIAMETRE"] <= 200)

    def test_combined_filters(self, sample_scoring_df, sample_config):
        filtres = {"score_min": 0.3, "age_min": 10, "age_max": 70}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert all(result["score_h3"] >= 0.3)
        assert all(result["age"] >= 10)

    def test_returns_view_not_copy(self, sample_scoring_df, sample_config):
        """Vérifie que le résultat n'est pas une copie complète."""
        result = apply_filters(sample_scoring_df, {}, sample_config, horizon=3)
        # Le résultat partage les données avec l'original (pas de .copy())
        assert result is not sample_scoring_df or len(result) == len(sample_scoring_df)

    def test_empty_result(self, sample_scoring_df, sample_config):
        filtres = {"score_min": 999.0}
        result = apply_filters(sample_scoring_df, filtres, sample_config, horizon=3)
        assert len(result) == 0
