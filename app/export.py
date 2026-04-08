"""Export CSV configurable avec sélection de colonnes."""

from datetime import datetime

import pandas as pd


def export_csv(df: pd.DataFrame, columns: list, config: dict) -> bytes:
    """Exporte le DataFrame filtré en CSV avec les colonnes sélectionnées."""
    export_cfg = config.get("export", {})
    sep = export_cfg.get("separator", ";")
    encoding = export_cfg.get("encoding", "utf-8")
    filtered_cols = [c for c in columns if c in df.columns]
    return df[filtered_cols].to_csv(index=False, sep=sep, encoding=encoding).encode(encoding)


def get_export_filename(prefix: str = "troncons") -> str:
    """Génère un nom horodaté pour l'export."""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d')}.csv"
