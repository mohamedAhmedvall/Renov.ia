"""Tests de contrat + parcours e2e de l'API (raccord Tab. 16 du mémoire).

- Contrat : les réponses valident les DTO pydantic et l'OpenAPI expose bien
  les routes — le front peut être développé contre ce contrat sans le serveur.
- E2E : parcours complet ville → filtres → KPI → carte → tableau → EDA →
  scénario d'optimisation, via TestClient (ASGI in-process).
"""

from fastapi.testclient import TestClient

from backend.app.dto import EdaDTO, KpiDTO, OptimisationResponse, TronconDTO, VilleDTO
from backend.app.main import app

client = TestClient(app)

VILLE = "marseille"


def _villes() -> list[VilleDTO]:
    return [VilleDTO(**v) for v in client.get("/api/villes").json()]


# ---------- Contrat ----------

def test_openapi_expose_les_routes():
    spec = client.get("/openapi.json").json()
    attendues = (
        "/api/villes", "/api/materiaux", "/api/kpi", "/api/troncons",
        "/api/troncons/{id_troncon}", "/api/geojson", "/api/eda", "/api/optimiser",
    )
    for route in attendues:
        assert route in spec["paths"], f"Route absente du contrat : {route}"


def test_contrat_villes():
    villes = _villes()
    assert len(villes) >= 2, "la démo doit proposer plusieurs villes"
    assert all(-90 <= v.centre_lat <= 90 and -180 <= v.centre_lon <= 180 for v in villes)


def test_contrat_kpi():
    kpi = KpiDTO(**client.get("/api/kpi", params={"ville": VILLE}).json())
    assert kpi.lineaire_km > 0
    assert kpi.nb_troncons > 0
    assert kpi.cout_renouvellement_euros > 0


def test_contrat_troncons_respecte_le_filtre_de_notes():
    r = client.get("/api/troncons", params={"ville": VILLE, "notes": [4, 5], "limit": 50})
    assert r.status_code == 200
    rows = [TronconDTO(**t) for t in r.json()]
    assert rows, "aucun tronçon note >= 4 dans le jeu synthétique"
    assert all(t.note_h3 in (4, 5) for t in rows)


def test_contrat_troncon_unitaire():
    """La fiche doit rester accessible hors filtres : la carte affiche plus que le tableau."""
    premier = client.get("/api/troncons", params={"ville": VILLE, "limit": 1}).json()[0]
    r = client.get(f"/api/troncons/{premier['id_troncon']}", params={"ville": VILLE})
    assert r.status_code == 200
    assert TronconDTO(**r.json()).id_troncon == premier["id_troncon"]

    assert client.get("/api/troncons/INCONNU", params={"ville": VILLE}).status_code == 404


def test_contrat_eda():
    eda = EdaDTO(**client.get("/api/eda", params={"ville": VILLE}).json())
    assert len(eda.notes) == 5
    assert eda.casses_par_materiau and eda.poses_par_decennie
    assert 0 <= eda.capture_20pct <= 1
    # La courbe de capture part de l'origine et progresse.
    assert eda.courbe_capture[0].x == 0 and eda.courbe_capture[0].y == 0
    assert eda.courbe_capture[-1].x >= 0.99


def test_ville_inconnue_est_rejetee():
    assert client.get("/api/kpi", params={"ville": "atlantide"}).status_code == 404


def test_contrat_optimisation_rejette_horizon_invalide():
    r = client.post("/api/optimiser", json={"budget_euros": 100000, "horizon": 2})
    assert r.status_code == 422


# ---------- Géoréférencement ----------

def test_geojson_est_ancre_sur_la_ville():
    """Le réseau simulé doit tomber sur le fond de carte de la ville demandée."""
    for ville in _villes():
        geo = client.get("/api/geojson", params={"ville": ville.cle}).json()
        assert geo["type"] == "FeatureCollection" and geo["features"]
        lons, lats = zip(
            *[p for f in geo["features"] for p in f["geometry"]["coordinates"]], strict=True
        )
        # Emprise attendue : quelques kilomètres autour du centre, pas l'autre bout du pays.
        assert max(abs(la - ville.centre_lat) for la in lats) < 0.1, ville.nom
        assert max(abs(lo - ville.centre_lon) for lo in lons) < 0.1, ville.nom


def test_emprise_dessinee_reduit_le_perimetre():
    ville = _villes()[0]
    total = KpiDTO(**client.get("/api/kpi", params={"ville": ville.cle}).json())
    petite = KpiDTO(
        **client.get(
            "/api/kpi",
            params={
                "ville": ville.cle,
                "bbox": f"{ville.centre_lon - 0.005},{ville.centre_lat - 0.005},"
                f"{ville.centre_lon + 0.005},{ville.centre_lat + 0.005}",
            },
        ).json()
    )
    assert 0 < petite.nb_troncons < total.nb_troncons
    assert petite.lineaire_km < total.lineaire_km


def test_bbox_malformee_est_rejetee():
    assert client.get("/api/kpi", params={"ville": VILLE, "bbox": "nawak"}).status_code == 422


# ---------- E2E ----------

def test_e2e_parcours_decision():
    """Parcours complet : santé → KPI → tableau priorisé → carte → EDA → scénario budgété."""
    assert client.get("/health").json()["donnees"] == "synthetiques"

    filtres = {"ville": VILLE, "notes": [4, 5]}
    kpi = KpiDTO(**client.get("/api/kpi", params=filtres).json())

    top = client.get("/api/troncons", params={**filtres, "limit": 10}).json()
    scores = [t["score_h3"] for t in top if t["score_h3"] is not None]
    assert scores == sorted(scores, reverse=True), "le tableau doit être trié par risque"

    geo = client.get("/api/geojson", params=filtres).json()
    assert len(geo["features"]) == kpi.nb_troncons, "carte et KPI décrivent le même périmètre"

    eda = EdaDTO(**client.get("/api/eda", params=filtres).json())
    assert eda.nb_troncons == kpi.nb_troncons, "EDA et KPI décrivent le même périmètre"

    r = client.post("/api/optimiser", params=filtres, json={"budget_euros": 2_000_000, "horizon": 3})
    assert r.status_code == 200
    sc = OptimisationResponse(**r.json())
    assert 0 < sc.cout_total <= 2_000_000
    assert sc.casses_evitees > 0
    assert sc.lineaire_km < kpi.lineaire_km


def test_e2e_rendement_marginal_decroissant():
    """Doubler le budget ne double pas les casses évitées (greedy prend le meilleur d'abord)."""
    def scenario(budget: float) -> OptimisationResponse:
        r = client.post(
            "/api/optimiser", params={"ville": VILLE}, json={"budget_euros": budget, "horizon": 3}
        )
        return OptimisationResponse(**r.json())

    r1, r2 = scenario(1_000_000), scenario(2_000_000)
    assert r2.casses_evitees >= r1.casses_evitees
    if r1.casses_evitees > 0:
        assert r2.casses_evitees < 2 * r1.casses_evitees


def test_e2e_les_villes_ont_des_profils_distincts():
    """Le sélecteur de ville doit changer les chiffres, pas seulement le fond de carte."""
    ages = {}
    for ville in _villes():
        kpi = KpiDTO(**client.get("/api/kpi", params={"ville": ville.cle}).json())
        ages[ville.nom] = kpi.age_moyen_ans
    assert len(set(ages.values())) == len(ages), f"âges moyens non distincts : {ages}"
    assert max(ages.values()) - min(ages.values()) > 3, f"écart d'âge trop faible : {ages}"
