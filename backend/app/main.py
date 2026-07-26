"""API FastAPI Renov.ia (démo publique) — passerelle REST vers le domaine.

Aucune logique métier ici : l'API charge les données via le Repository,
délègue au domaine (typologie, conséquence, notes) et à l'optimiseur, puis
traduit en DTO. C'est le rôle « passerelle » : contrats stables côté front,
domaine substituable côté serveur.

Le réseau est simulé par ville (`data/synthetic/<ville>/`). Les coordonnées
stockées sont locales, en mètres autour du centre-ville ; l'API les projette en
WGS84 pour l'affichage sur fond de carte. Le centre réel de la ville n'est
qu'un ancrage cartographique : la géométrie du réseau est entièrement fictive.

Lancement : uvicorn backend.app.main:app --port 8000
"""

import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.dto import (
    EdaDTO,
    KpiDTO,
    OptimisationRequest,
    OptimisationResponse,
    PointDTO,
    SerieDTO,
    TronconDTO,
    VilleDTO,
)
from domain import DEFAULT_CONFIG, compute_notes
from domain.repository import CsvTronconRepository
from optimizer import cout_remplacement, optimize_renewal

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "synthetic"
FRONT_DIST = ROOT / "frontend" / "dist"

ANNEE_REF = 2024          # année de scoring du pipeline ML
FENETRE_CASSES = 10       # profondeur d'historique affichée par tronçon
METRES_PAR_DEGRE = 111_320.0

VILLES: dict[str, dict] = json.loads((DATA_DIR / "villes.json").read_text(encoding="utf-8"))["villes"]
VILLE_DEFAUT = next(iter(VILLES))

app = FastAPI(
    title="Renov.ia — API de démonstration",
    description="Scoring prédictif de défaillance et priorisation du renouvellement. "
    "Données 100 % synthétiques.",
    version="2.0.0",
)

# En développement, le front Vite (5173) appelle l'API sur un autre port : CORS
# nécessaire. En production le front compilé est servi par cette même application
# (voir le montage en fin de fichier), donc même origine et CORS sans objet.
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- chargement

@lru_cache(maxsize=8)
def _casses(ville: str) -> pd.DataFrame:
    """Historique de casses de la ville (une ligne par casse)."""
    return pd.read_csv(DATA_DIR / ville / "casses.csv")


@lru_cache(maxsize=8)
def _dataset(ville: str) -> pd.DataFrame:
    """Patrimoine scoré et enrichi par le domaine, mis en cache par ville.

    Les notes 1–5 sont calculées sur le patrimoine COMPLET de la ville : elles
    reposent sur des quantiles de risque, qui n'auraient plus de sens s'ils
    étaient recalculés à chaque filtre de l'utilisateur.
    """
    repo = CsvTronconRepository(DATA_DIR / ville)
    df = compute_notes(repo.get_troncons_scores(), DEFAULT_CONFIG)

    casses = _casses(ville)
    recentes = casses[casses["annee"] > ANNEE_REF - FENETRE_CASSES]
    df["casses_10ans"] = (
        df["id_troncon"].map(recentes.groupby("id_troncon").size()).fillna(0).astype(int)
    )
    abonnes = df["nb_abonne"] if "nb_abonne" in df.columns else pd.Series(0, index=df.index)
    df["population_desservie"] = pd.to_numeric(abonnes, errors="coerce").fillna(0).astype(int)
    df["cout_renouvellement_euros"] = cout_remplacement(df).round(0)
    return df


def _ville_valide(ville: str) -> str:
    if ville not in VILLES:
        raise HTTPException(status_code=404, detail=f"Ville inconnue : {ville}")
    return ville


# ------------------------------------------------------------------ filtres

@dataclass(frozen=True)
class Filtres:
    """Périmètre d'analyse, partagé par toutes les routes de lecture."""

    ville: str
    notes: tuple[int, ...]
    materiau: str | None
    pose_max: int
    bbox: tuple[float, float, float, float] | None


def filtres(
    ville: str = Query(default=VILLE_DEFAUT, description="Clé de ville (cf. /api/villes)"),
    notes: list[int] | None = Query(default=None, description="Notes 1–5 retenues, toutes si absent"),
    materiau: str | None = Query(default=None, description="Matériau exact, sinon tous"),
    pose_max: int = Query(default=2100, description="Ne garder que les poses ≤ cette année"),
    bbox: str | None = Query(default=None, description="lon_min,lat_min,lon_max,lat_max (WGS84)"),
) -> Filtres:
    """Dépendance FastAPI : un seul jeu de filtres pour carte, tableau, KPI et EDA."""
    emprise: tuple[float, float, float, float] | None = None
    if bbox:
        try:
            lon1, lat1, lon2, lat2 = (float(v) for v in bbox.split(","))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="bbox attendu : lon_min,lat_min,lon_max,lat_max"
            ) from None
        emprise = (min(lon1, lon2), min(lat1, lat2), max(lon1, lon2), max(lat1, lat2))
    retenues = tuple(n for n in notes or () if 1 <= n <= 5)
    return Filtres(
        ville=_ville_valide(ville),
        notes=retenues or (1, 2, 3, 4, 5),
        materiau=materiau or None,
        pose_max=pose_max,
        bbox=emprise,
    )


def _perimetre(f: Filtres, ignorer_notes: bool = False) -> pd.DataFrame:
    """Applique les filtres et trie par risque décroissant.

    `ignorer_notes` sert à la légende et à l'histogramme des notes : ils doivent
    dire combien de tronçons se cachent derrière une note DÉCOCHÉE, ce qu'un
    comptage sur le périmètre déjà filtré ne peut pas faire (il vaudrait zéro).
    """
    df = _dataset(f.ville)
    if not ignorer_notes and "note_h3" in df.columns:
        df = df[df["note_h3"].isin(f.notes)]
    if f.materiau:
        df = df[df["materiau"] == f.materiau]
    df = df[df["annee_pose"] <= f.pose_max]
    if f.bbox:
        # L'emprise est dessinée en WGS84 : on la ramène en coordonnées locales
        # plutôt que de projeter les milliers de tronçons à chaque requête.
        x_min, y_min = _vers_local(f.ville, f.bbox[0], f.bbox[1])
        x_max, y_max = _vers_local(f.ville, f.bbox[2], f.bbox[3])
        dans = ((df["x1"].between(x_min, x_max) & df["y1"].between(y_min, y_max))
                | (df["x2"].between(x_min, x_max) & df["y2"].between(y_min, y_max)))
        df = df[dans]
    if "score_h3" in df.columns:
        df = df.sort_values("score_h3", ascending=False)
    return df


# --------------------------------------------------------------- projection

def _vers_wgs84(ville: str, x: float, y: float) -> list[float]:
    """Mètres locaux → [longitude, latitude] autour du centre de la ville."""
    lat0, lon0 = VILLES[ville]["centre"]
    lat = lat0 + y / METRES_PAR_DEGRE
    lon = lon0 + x / (METRES_PAR_DEGRE * math.cos(math.radians(lat0)))
    return [round(lon, 6), round(lat, 6)]


def _vers_local(ville: str, lon: float, lat: float) -> tuple[float, float]:
    """Réciproque de `_vers_wgs84` (utilisée pour l'emprise dessinée)."""
    lat0, lon0 = VILLES[ville]["centre"]
    return (
        (lon - lon0) * METRES_PAR_DEGRE * math.cos(math.radians(lat0)),
        (lat - lat0) * METRES_PAR_DEGRE,
    )


# ------------------------------------------------------------------- routes

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "donnees": "synthetiques", "villes": list(VILLES)}


@app.get("/api/villes", response_model=list[VilleDTO])
def villes() -> list[VilleDTO]:
    """Villes disponibles et leur ancrage cartographique."""
    return [
        VilleDTO(
            cle=cle, nom=v["nom"], centre_lat=v["centre"][0], centre_lon=v["centre"][1],
            zoom=v["zoom"],
        )
        for cle, v in VILLES.items()
    ]


@app.get("/api/materiaux", response_model=list[str])
def materiaux(ville: str = Query(default=VILLE_DEFAUT)) -> list[str]:
    """Matériaux présents dans la ville, pour peupler le filtre sans le coder en dur."""
    return sorted(_dataset(_ville_valide(ville))["materiau"].dropna().unique().tolist())


@app.get("/api/kpi", response_model=KpiDTO)
def kpi(f: Filtres = Depends(filtres)) -> KpiDTO:
    """Six indicateurs du périmètre filtré."""
    df = _perimetre(f)
    if df.empty:
        return KpiDTO(
            lineaire_km=0.0, nb_troncons=0, lineaire_note5_km=0.0,
            age_moyen_ans=0.0, casses_attendues_h3=0.0, cout_renouvellement_euros=0.0,
        )
    note5 = df[df["note_h3"] == 5] if "note_h3" in df.columns else df.iloc[0:0]
    # Les probabilités calibrées ne s'additionnent pas : on passe au comptage de
    # Poisson μ = −ln(1−P), qui lui est additif (même formulation qu'optimizer.greedy).
    brut = df["score_h3"] if "score_h3" in df.columns else pd.Series(0.0, index=df.index)
    proba = pd.to_numeric(brut, errors="coerce").fillna(0).clip(0, 0.999999)
    return KpiDTO(
        lineaire_km=round(float(df["longueur_m"].sum()) / 1000.0, 1),
        nb_troncons=len(df),
        lineaire_note5_km=round(float(note5["longueur_m"].sum()) / 1000.0, 1),
        age_moyen_ans=round(float((ANNEE_REF - df["annee_pose"]).mean()), 1),
        casses_attendues_h3=round(float(-np.log(1.0 - proba).sum()), 1),
        cout_renouvellement_euros=round(float(df["cout_renouvellement_euros"].sum()), 0),
    )


@app.get("/api/troncons", response_model=list[TronconDTO])
def troncons(
    f: Filtres = Depends(filtres),
    limit: int = Query(default=300, le=5000),
) -> list[TronconDTO]:
    """Tronçons du périmètre, triés par risque décroissant."""
    rows = _perimetre(f).head(limit).to_dict(orient="records")
    # model_validate (plutôt que **kwargs) : pydantic valide les types à l'exécution,
    # ce que mypy ne peut pas prouver statiquement sur des dicts issus de pandas.
    return [
        TronconDTO.model_validate({k: r.get(k) for k in TronconDTO.model_fields}) for r in rows
    ]


@app.get("/api/troncons/{id_troncon}", response_model=TronconDTO)
def troncon(id_troncon: str, ville: str = Query(default=VILLE_DEFAUT)) -> TronconDTO:
    """Un tronçon par identifiant, hors filtres.

    La carte affiche tout le périmètre alors que le tableau est plafonné : sans
    cette route, cliquer un tronçon peu risqué sur la carte ne donnerait aucune
    fiche.
    """
    df = _dataset(_ville_valide(ville))
    trouve = df[df["id_troncon"] == id_troncon]
    if trouve.empty:
        raise HTTPException(status_code=404, detail=f"Tronçon inconnu : {id_troncon}")
    r = trouve.iloc[0].to_dict()
    return TronconDTO.model_validate({k: r.get(k) for k in TronconDTO.model_fields})


@app.get("/api/geojson")
def geojson(f: Filtres = Depends(filtres)) -> dict:
    """FeatureCollection GeoJSON du périmètre (LineString en WGS84)."""
    df = _perimetre(f)
    features = [
        {
            "type": "Feature",
            "properties": {
                "id": r["id_troncon"],
                "note": int(r.get("note_h3") or 1),
                "score_h3": r.get("score_h3"),
                "materiau": r["materiau"],
                "diametre_mm": int(r["diametre_mm"]),
                "annee_pose": int(r["annee_pose"]),
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    _vers_wgs84(f.ville, r["x1"], r["y1"]),
                    _vers_wgs84(f.ville, r["x2"], r["y2"]),
                ],
            },
        }
        for r in df.to_dict(orient="records")
        if pd.notna(r.get("x1"))
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/eda", response_model=EdaDTO)
def eda(f: Filtres = Depends(filtres)) -> EdaDTO:
    """Agrégats d'exploration du périmètre filtré (six séries prêtes à tracer)."""
    df = _perimetre(f)
    if df.empty:
        return EdaDTO(
            nb_troncons=0, notes=[], casses_par_materiau=[], poses_par_decennie=[],
            lineaire_par_materiau_km=[], casses_par_annee=[], courbe_capture=[],
            capture_20pct=0.0,
        )

    casses = _casses(f.ville)
    casses = casses[casses["id_troncon"].isin(df["id_troncon"])]
    mat_par_id = df.set_index("id_troncon")["materiau"]

    avant_notes = _perimetre(f, ignorer_notes=True)
    notes = [
        SerieDTO(cle=str(n), valeur=float((avant_notes["note_h3"] == n).sum()))
        for n in (1, 2, 3, 4, 5)
    ]
    par_mat = casses["id_troncon"].map(mat_par_id).value_counts()
    casses_mat = [SerieDTO(cle=str(m), valeur=float(v)) for m, v in par_mat.items()]
    lin_mat = [
        SerieDTO(cle=str(m), valeur=round(float(v) / 1000.0, 2))
        for m, v in df.groupby("materiau")["longueur_m"].sum().sort_values(ascending=False).items()
    ]
    decennies = (df["annee_pose"] // 10 * 10).value_counts().sort_index()
    poses = [SerieDTO(cle=str(d), valeur=float(v)) for d, v in decennies.items()]
    par_an = casses["annee"].value_counts()
    annees = [
        SerieDTO(cle=str(a), valeur=float(par_an.get(a, 0)))
        for a in range(ANNEE_REF - FENETRE_CASSES + 1, ANNEE_REF + 1)
    ]

    courbe, capture = _courbe_capture(df, casses)
    return EdaDTO(
        nb_troncons=len(df), notes=notes, casses_par_materiau=casses_mat,
        poses_par_decennie=poses, lineaire_par_materiau_km=lin_mat, casses_par_annee=annees,
        courbe_capture=courbe, capture_20pct=capture,
    )


def _courbe_capture(df: pd.DataFrame, casses: pd.DataFrame) -> tuple[list[PointDTO], float]:
    """Part des casses observées captée en priorisant par risque au mètre.

    C'est la métrique métier du backtest (`ml/backtest`) appliquée au périmètre
    affiché : la diagonale correspond à une priorisation aléatoire.
    """
    tri = df.assign(risque_m=df["score_h3"].fillna(0) / df["longueur_m"].clip(lower=1))
    tri = tri.sort_values("risque_m", ascending=False)
    nb_casses = tri["id_troncon"].map(casses["id_troncon"].value_counts()).fillna(0)

    lin_cum = tri["longueur_m"].cumsum() / max(float(tri["longueur_m"].sum()), 1.0)
    cas_cum = nb_casses.cumsum() / max(float(nb_casses.sum()), 1.0)

    # Une courbe de 2 000 points serait illisible à l'écran : on échantillonne.
    pas = max(1, len(tri) // 120)
    points = [PointDTO(x=0.0, y=0.0)] + [
        PointDTO(x=round(float(x), 4), y=round(float(y), 4))
        for x, y in zip(lin_cum[::pas], cas_cum[::pas], strict=True)
    ]
    if points[-1].x < 1.0:
        points.append(PointDTO(x=1.0, y=1.0))
    capture = next((p.y for p in points if p.x >= 0.2), 0.0)
    return points, round(capture, 3)


@app.post("/api/optimiser", response_model=OptimisationResponse)
def optimiser(req: OptimisationRequest, f: Filtres = Depends(filtres)) -> OptimisationResponse:
    """Scénario de renouvellement optimal sous budget, dans le périmètre filtré."""
    if req.horizon not in (1, 3, 5):
        raise HTTPException(status_code=422, detail="horizon doit être 1, 3 ou 5")
    df = _perimetre(f)
    if f"score_h{req.horizon}" not in df.columns:
        raise HTTPException(
            status_code=503, detail="Scores absents : lancer `python ml/run_pipeline.py`."
        )
    if df.empty:
        return OptimisationResponse(
            horizon=req.horizon, budget=req.budget_euros, cout_total=0.0, nb_troncons=0,
            lineaire_km=0.0, casses_evitees=0.0, casses_evitees_ic95=0.0, ids=[],
        )
    result = optimize_renewal(df, budget=req.budget_euros, params={"horizon": req.horizon})
    return OptimisationResponse(**result)


# Front compilé servi par la même application quand il est présent (image Docker).
# Monté en dernier : les routes /api, /health et /docs déclarées ci-dessus restent
# prioritaires, le reste retombe sur index.html. Absent en développement, où Vite
# sert le front lui-même.
if FRONT_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONT_DIST, html=True), name="front")
