"""Contrats DTO de l'API (pydantic) — la frontière typée entre domaine et clients.

Les DTO sont le CONTRAT : le front (et les tests de contrat) ne dépendent que
de ces schémas, jamais des DataFrames internes. Toute évolution du domaine qui
casse un DTO casse d'abord un test de contrat — pas la démo devant un client.
"""

from pydantic import BaseModel, Field


class TronconDTO(BaseModel):
    """Un tronçon scoré, tel qu'exposé au front."""

    id_troncon: str
    famille_materiau: str
    materiau: str
    diametre_mm: int
    longueur_m: float
    annee_pose: int
    typologie: str
    consequence: float = Field(ge=0, le=1)
    score_h1: float | None = Field(default=None, ge=0, le=1)
    score_h3: float | None = Field(default=None, ge=0, le=1)
    score_h5: float | None = Field(default=None, ge=0, le=1)
    note_h3: int | None = Field(default=None, ge=1, le=5)


class KpiDTO(BaseModel):
    """KPI réseau — le métier raisonne en LINÉAIRE (km), pas en nombre de tronçons."""

    lineaire_total_km: float
    lineaire_note5_km: float
    nb_troncons: int
    age_moyen_ans: float


class OptimisationRequest(BaseModel):
    budget_euros: float = Field(gt=0, description="Budget de renouvellement (€)")
    horizon: int = Field(default=3, description="Horizon de risque (1, 3 ou 5 ans)")


class OptimisationResponse(BaseModel):
    horizon: int
    budget: float
    cout_total: float
    nb_troncons: int
    lineaire_km: float
    casses_evitees: float
    casses_evitees_ic95: float
    ids: list[str]


class GeoFeatureDTO(BaseModel):
    """Feature GeoJSON minimale d'un tronçon (LineString en coordonnées locales)."""

    type: str = "Feature"
    properties: dict
    geometry: dict
