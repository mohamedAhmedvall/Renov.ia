"""API FastAPI Renov.ia (démo publique) — passerelle REST vers le domaine.

Aucune logique métier ici : l'API charge les données via le Repository,
délègue au domaine (notes) et à l'optimiseur, puis traduit en DTO. C'est le
rôle « passerelle » : contrats stables côté front, domaine substituable côté
serveur.

Lancement : uvicorn backend.app.main:app --port 8000
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.app.dto import (
    KpiDTO,
    OptimisationRequest,
    OptimisationResponse,
    TronconDTO,
)
from domain import DEFAULT_CONFIG, compute_notes
from domain.repository import CsvTronconRepository
from optimizer import optimize_renewal

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "synthetic"

app = FastAPI(
    title="Renov.ia — API de démonstration",
    description="Scoring prédictif de défaillance et priorisation du renouvellement. "
    "Données 100 % synthétiques.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _dataset() -> pd.DataFrame:
    """Tronçons + scores + typologie/conséquence/notes (calcul domaine, mis en cache)."""
    repo = CsvTronconRepository(DATA_DIR)
    df = repo.get_troncons_scores()
    return compute_notes(df, DEFAULT_CONFIG)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "donnees": "synthetiques"}


@app.get("/api/kpi", response_model=KpiDTO)
def kpi() -> KpiDTO:
    df = _dataset()
    note5 = df[df.get("note_h3", 0) == 5] if "note_h3" in df.columns else df.iloc[0:0]
    return KpiDTO(
        lineaire_total_km=round(float(df["longueur_m"].sum()) / 1000.0, 1),
        lineaire_note5_km=round(float(note5["longueur_m"].sum()) / 1000.0, 1),
        nb_troncons=len(df),
        age_moyen_ans=round(float((2024 - df["annee_pose"]).mean()), 1),
    )


@app.get("/api/troncons", response_model=list[TronconDTO])
def troncons(
    note_min: int = Query(default=1, ge=1, le=5),
    limit: int = Query(default=500, le=5000),
) -> list[TronconDTO]:
    """Tronçons scorés, triés par risque décroissant (filtre par note minimale)."""
    df = _dataset()
    if "note_h3" in df.columns:
        df = df[df["note_h3"] >= note_min].sort_values("score_h3", ascending=False)
    rows = df.head(limit).to_dict(orient="records")
    # model_validate (plutôt que **kwargs) : pydantic valide les types à l'exécution,
    # ce que mypy ne peut pas prouver statiquement sur des dicts issus de pandas.
    return [
        TronconDTO.model_validate({k: r.get(k) for k in TronconDTO.model_fields}) for r in rows
    ]


@app.get("/api/geojson")
def geojson(note_min: int = Query(default=1, ge=1, le=5)) -> dict:
    """FeatureCollection GeoJSON des tronçons (LineString, coordonnées locales en m)."""
    df = _dataset()
    if "note_h3" in df.columns:
        df = df[df["note_h3"] >= note_min]
    features = [
        {
            "type": "Feature",
            "properties": {
                "id": r["id_troncon"],
                "note": int(r.get("note_h3") or 1),
                "score_h3": r.get("score_h3"),
                "materiau": r["materiau"],
                "diametre_mm": int(r["diametre_mm"]),
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[r["x1"], r["y1"]], [r["x2"], r["y2"]]],
            },
        }
        for r in df.to_dict(orient="records")
        if pd.notna(r.get("x1"))
    ]
    return {"type": "FeatureCollection", "features": features}


@app.post("/api/optimiser", response_model=OptimisationResponse)
def optimiser(req: OptimisationRequest) -> OptimisationResponse:
    """Scénario de renouvellement optimal sous contrainte de budget."""
    if req.horizon not in (1, 3, 5):
        raise HTTPException(status_code=422, detail="horizon doit être 1, 3 ou 5")
    df = _dataset()
    if f"score_h{req.horizon}" not in df.columns:
        raise HTTPException(
            status_code=503, detail="Scores absents : lancer `python ml/run_pipeline.py`."
        )
    result = optimize_renewal(df, budget=req.budget_euros, params={"horizon": req.horizon})
    return OptimisationResponse(**result)
