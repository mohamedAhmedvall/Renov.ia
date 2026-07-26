"""Contrats DTO de l'API (pydantic) — la frontière typée entre domaine et clients.

Les DTO sont le CONTRAT : le front (et les tests de contrat) ne dépendent que
de ces schémas, jamais des DataFrames internes. Toute évolution du domaine qui
casse un DTO casse d'abord un test de contrat — pas la démo devant un client.
"""

from pydantic import BaseModel, Field


class VilleDTO(BaseModel):
    """Une ville de démonstration : ancrage cartographique du réseau simulé."""

    cle: str
    nom: str
    centre_lat: float
    centre_lon: float
    zoom: int


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
    population_desservie: int
    casses_10ans: int
    cout_renouvellement_euros: float
    score_h1: float | None = Field(default=None, ge=0, le=1)
    score_h3: float | None = Field(default=None, ge=0, le=1)
    score_h5: float | None = Field(default=None, ge=0, le=1)
    note_h3: int | None = Field(default=None, ge=1, le=5)


class KpiDTO(BaseModel):
    """KPI du périmètre filtré — le métier raisonne en LINÉAIRE (km), pas en tronçons."""

    lineaire_km: float
    nb_troncons: int
    lineaire_note5_km: float
    age_moyen_ans: float
    casses_attendues_h3: float
    cout_renouvellement_euros: float


class SerieDTO(BaseModel):
    """Un point d'une série agrégée (histogramme, barres)."""

    cle: str
    valeur: float


class PointDTO(BaseModel):
    """Un point de la courbe de capture, en fractions cumulées [0,1]."""

    x: float
    y: float


class EdaDTO(BaseModel):
    """Agrégats d'exploration du périmètre filtré, calculés côté serveur.

    L'agrégation reste dans la passerelle plutôt que dans le navigateur : le
    front n'a jamais besoin de télécharger les milliers de tronçons ni
    l'historique de casses pour dessiner six graphiques.
    """

    nb_troncons: int
    notes: list[SerieDTO]
    casses_par_materiau: list[SerieDTO]
    poses_par_decennie: list[SerieDTO]
    lineaire_par_materiau_km: list[SerieDTO]
    casses_par_annee: list[SerieDTO]
    courbe_capture: list[PointDTO]
    capture_20pct: float


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
    """Feature GeoJSON d'un tronçon (LineString en WGS84)."""

    type: str = "Feature"
    properties: dict
    geometry: dict
