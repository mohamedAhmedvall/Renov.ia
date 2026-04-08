"""Tests pour le module data_loader (fonctions pures, sans Streamlit)."""

import pandas as pd
import pytest

from data_loader import _cast_numeric, _classify_risk, _compute_icp, _validate_columns


class TestValidateColumns:
    def test_all_present(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        assert _validate_columns(df, ["a", "b"], "test") == []

    def test_missing_columns(self):
        df = pd.DataFrame({"a": [1]})
        missing = _validate_columns(df, ["a", "b", "c"], "test")
        assert "b" in missing
        assert "c" in missing

    def test_empty_required(self):
        df = pd.DataFrame({"a": [1]})
        assert _validate_columns(df, [], "test") == []


class TestCastNumeric:
    def test_float_casting(self):
        df = pd.DataFrame({"val": ["1.5", "2,3", "abc"]})
        result, warnings = _cast_numeric(df, {"val": "float"})
        assert result["val"].iloc[0] == pytest.approx(1.5)
        assert result["val"].iloc[1] == pytest.approx(2.3)
        assert pd.isna(result["val"].iloc[2])
        assert "val" in warnings

    def test_int_casting(self):
        df = pd.DataFrame({"val": [1.5, None, 3.0]})
        result, _ = _cast_numeric(df, {"val": "int"})
        assert result["val"].iloc[1] == 0  # NaN filled with 0

    def test_str_casting_handles_nan(self):
        df = pd.DataFrame({"val": [None, "hello", float("nan")]})
        result, _ = _cast_numeric(df, {"val": "str"})
        assert result["val"].iloc[0] == ""
        assert result["val"].iloc[1] == "hello"

    def test_str_casting_replaces_nan_string(self):
        df = pd.DataFrame({"val": ["nan", "None", "valid"]})
        result, _ = _cast_numeric(df, {"val": "str"})
        assert result["val"].iloc[0] == ""
        assert result["val"].iloc[1] == ""
        assert result["val"].iloc[2] == "valid"

    def test_missing_column_skipped(self):
        df = pd.DataFrame({"a": [1]})
        result, warnings = _cast_numeric(df, {"missing_col": "float"})
        assert len(warnings) == 0

    def test_float_with_spaces(self):
        df = pd.DataFrame({"val": [" 1.5 ", " 2,3 "]})
        result, _ = _cast_numeric(df, {"val": "float"})
        assert result["val"].iloc[0] == pytest.approx(1.5)
        assert result["val"].iloc[1] == pytest.approx(2.3)


class TestClassifyRisk:
    def test_critique(self):
        thresholds = {"critique": 0.8, "eleve": 0.6, "modere": 0.3}
        assert _classify_risk(0.9, thresholds) == "critique"

    def test_eleve(self):
        thresholds = {"critique": 0.8, "eleve": 0.6, "modere": 0.3}
        assert _classify_risk(0.7, thresholds) == "eleve"

    def test_modere(self):
        thresholds = {"critique": 0.8, "eleve": 0.6, "modere": 0.3}
        assert _classify_risk(0.4, thresholds) == "modere"

    def test_faible(self):
        thresholds = {"critique": 0.8, "eleve": 0.6, "modere": 0.3}
        assert _classify_risk(0.1, thresholds) == "faible"

    def test_boundary_critique(self):
        thresholds = {"critique": 0.8, "eleve": 0.6, "modere": 0.3}
        assert _classify_risk(0.8, thresholds) == "critique"


class TestComputeIcp:
    def test_all_filled(self):
        df = pd.DataFrame({"MATERIAU": ["Fonte"], "DIAMETRE": [150.0], "LONGUEUR": [100.0], "POSE": ["1970"], "age": [50.0]})
        icp = _compute_icp(df)
        assert icp.iloc[0] == 100.0

    def test_half_filled(self):
        df = pd.DataFrame({"MATERIAU": ["Fonte"], "DIAMETRE": [None], "age": [None]})
        icp = _compute_icp(df)
        assert 0 < icp.iloc[0] < 100

    def test_no_icp_fields(self):
        df = pd.DataFrame({"other_col": [1]})
        icp = _compute_icp(df)
        assert icp.iloc[0] == 0.0
