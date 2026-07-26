/** Client API typé — seul point de contact avec le backend (contrats DTO). */

/**
 * Année à laquelle le pipeline ML calcule les scores de production
 * (`ml/run_pipeline.py`). Les âges affichés se comptent à partir d'elle, pas de
 * la date du jour : le patrimoine n'a pas vieilli depuis le dernier scoring.
 */
export const ANNEE_REFERENCE = 2024;

export interface Ville {
  cle: string;
  nom: string;
  centre_lat: number;
  centre_lon: number;
  zoom: number;
}

export interface Troncon {
  id_troncon: string;
  famille_materiau: string;
  materiau: string;
  diametre_mm: number;
  longueur_m: number;
  annee_pose: number;
  typologie: string;
  consequence: number;
  population_desservie: number;
  casses_10ans: number;
  cout_renouvellement_euros: number;
  score_h1: number | null;
  score_h3: number | null;
  score_h5: number | null;
  note_h3: number | null;
}

export interface Kpi {
  lineaire_km: number;
  nb_troncons: number;
  lineaire_note5_km: number;
  age_moyen_ans: number;
  casses_attendues_h3: number;
  cout_renouvellement_euros: number;
}

export interface Serie {
  cle: string;
  valeur: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface Eda {
  nb_troncons: number;
  notes: Serie[];
  casses_par_materiau: Serie[];
  poses_par_decennie: Serie[];
  lineaire_par_materiau_km: Serie[];
  casses_par_annee: Serie[];
  courbe_capture: Point[];
  capture_20pct: number;
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

/** Emprise dessinée sur la carte : [lon_min, lat_min, lon_max, lat_max]. */
export type Bbox = [number, number, number, number];

export interface Filtres {
  ville: string;
  notes: number[];
  materiau: string;
  poseMax: number;
  bbox: Bbox | null;
}

/**
 * Les cinq filtres voyagent ensemble vers toutes les routes de lecture : c'est
 * ce qui garantit que KPI, carte, tableau et EDA décrivent le même périmètre.
 */
function parametres(f: Filtres): string {
  const p = new URLSearchParams({ ville: f.ville, pose_max: String(f.poseMax) });
  for (const n of f.notes) p.append("notes", String(n));
  if (f.materiau) p.set("materiau", f.materiau);
  if (f.bbox) p.set("bbox", f.bbox.join(","));
  return p.toString();
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`API ${res.status} : ${await res.text()}`);
  return res.json() as Promise<T>;
}

function lire<T>(chemin: string, signal?: AbortSignal): Promise<T> {
  return fetch(chemin, { signal }).then((r) => json<T>(r));
}

export const api = {
  villes: (signal?: AbortSignal) => lire<Ville[]>("/api/villes", signal),
  materiaux: (ville: string, signal?: AbortSignal) =>
    lire<string[]>(`/api/materiaux?ville=${encodeURIComponent(ville)}`, signal),
  kpi: (f: Filtres, signal?: AbortSignal) => lire<Kpi>(`/api/kpi?${parametres(f)}`, signal),
  troncons: (f: Filtres, limite = 300, signal?: AbortSignal) =>
    lire<Troncon[]>(`/api/troncons?${parametres(f)}&limit=${limite}`, signal),
  troncon: (ville: string, id: string, signal?: AbortSignal) =>
    lire<Troncon>(
      `/api/troncons/${encodeURIComponent(id)}?ville=${encodeURIComponent(ville)}`,
      signal,
    ),
  geojson: (f: Filtres, signal?: AbortSignal) =>
    lire<GeoJSON.FeatureCollection>(`/api/geojson?${parametres(f)}`, signal),
  eda: (f: Filtres, signal?: AbortSignal) => lire<Eda>(`/api/eda?${parametres(f)}`, signal),
  optimiser: (f: Filtres, budgetEuros: number, horizon = 3) =>
    fetch(`/api/optimiser?${parametres(f)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ budget_euros: budgetEuros, horizon }),
    }).then((r) => json<Scenario>(r)),
};
