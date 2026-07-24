/** Client API typé — seul point de contact avec le backend (contrats DTO). */

export interface Kpi {
  lineaire_total_km: number;
  lineaire_note5_km: number;
  nb_troncons: number;
  age_moyen_ans: number;
}

export interface Troncon {
  id_troncon: string;
  materiau: string;
  diametre_mm: number;
  longueur_m: number;
  annee_pose: number;
  typologie: string;
  consequence: number;
  score_h3: number | null;
  note_h3: number | null;
}

export interface Scenario {
  horizon: number;
  budget: number;
  cout_total: number;
  nb_troncons: number;
  lineaire_km: number;
  casses_evitees: number;
  casses_evitees_ic95: number;
  ids: string[];
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`API ${res.status} : ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  kpi: () => fetch("/api/kpi").then((r) => json<Kpi>(r)),
  troncons: (noteMin: number, limit = 200) =>
    fetch(`/api/troncons?note_min=${noteMin}&limit=${limit}`).then((r) => json<Troncon[]>(r)),
  geojson: (noteMin: number) =>
    fetch(`/api/geojson?note_min=${noteMin}`).then((r) => json<GeoJSON.FeatureCollection>(r)),
  optimiser: (budgetEuros: number, horizon = 3) =>
    fetch("/api/optimiser", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ budget_euros: budgetEuros, horizon }),
    }).then((r) => json<Scenario>(r)),
};
