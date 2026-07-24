"""Tests de contrat + parcours e2e de l'API (raccord Tab. 16 du mémoire).

- Contrat : les réponses valident les DTO pydantic et l'OpenAPI expose bien
  les routes — le front peut être développé contre ce contrat sans le serveur.
- E2E : parcours complet KPI → tableau → carte → scénario d'optimisation sur
  le jeu synthétique, via TestClient (ASGI in-process).
"""

from fastapi.testclient import TestClient

from backend.app.dto import KpiDTO, OptimisationResponse, TronconDTO
from backend.app.main import app

client = TestClient(app)


# ---------- Contrat ----------

def test_openapi_expose_les_routes():
    spec = client.get("/openapi.json").json()
    for route in ("/api/kpi", "/api/troncons", "/api/geojson", "/api/optimiser"):
        assert route in spec["paths"], f"Route absente du contrat : {route}"


def test_contrat_kpi():
    r = client.get("/api/kpi")
    assert r.status_code == 200
    kpi = KpiDTO(**r.json())  # lève si le contrat est rompu
    assert kpi.lineaire_total_km > 0


def test_contrat_troncons():
    r = client.get("/api/troncons", params={"note_min": 4, "limit": 50})
    assert r.status_code == 200
    rows = [TronconDTO(**t) for t in r.json()]
    assert rows, "aucun tronçon note >= 4 dans le jeu synthétique"
    assert all(t.note_h3 is None or t.note_h3 >= 4 for t in rows)


def test_contrat_optimisation_rejette_horizon_invalide():
    r = client.post("/api/optimiser", json={"budget_euros": 100000, "horizon": 2})
    assert r.status_code == 422


# ---------- E2E ----------

def test_e2e_parcours_decision():
    """Parcours complet : santé → KPI → tableau priorisé → carte → scénario budgété."""
    assert client.get("/health").json()["donnees"] == "synthetiques"

    kpi = KpiDTO(**client.get("/api/kpi").json())

    top = client.get("/api/troncons", params={"note_min": 1, "limit": 10}).json()
    scores = [t["score_h3"] for t in top if t["score_h3"] is not None]
    assert scores == sorted(scores, reverse=True), "le tableau doit être trié par risque"

    geo = client.get("/api/geojson", params={"note_min": 5}).json()
    assert geo["type"] == "FeatureCollection" and geo["features"]

    r = client.post("/api/optimiser", json={"budget_euros": 2_000_000, "horizon": 3})
    assert r.status_code == 200
    sc = OptimisationResponse(**r.json())
    assert 0 < sc.cout_total <= 2_000_000
    assert sc.casses_evitees > 0
    assert sc.lineaire_km < kpi.lineaire_total_km


def test_e2e_rendement_marginal_decroissant():
    """Doubler le budget ne double pas les casses évitées (greedy prend le meilleur d'abord)."""
    r1 = OptimisationResponse(
        **client.post("/api/optimiser", json={"budget_euros": 1_000_000, "horizon": 3}).json()
    )
    r2 = OptimisationResponse(
        **client.post("/api/optimiser", json={"budget_euros": 2_000_000, "horizon": 3}).json()
    )
    assert r2.casses_evitees >= r1.casses_evitees
    if r1.casses_evitees > 0:
        assert r2.casses_evitees < 2 * r1.casses_evitees
