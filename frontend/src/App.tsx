/**
 * Vue tronçons : un périmètre, quatre lectures.
 *
 * Les cinq filtres (ville, notes, matériau, année de pose, emprise dessinée)
 * définissent UN périmètre, envoyé tel quel à toutes les routes de lecture.
 * Carte, EDA, tableau et scénario décrivent donc toujours le même sous-réseau :
 * c'est ce qui permet de dessiner un quartier puis de basculer d'onglet sans
 * jamais se demander « de quoi parle ce chiffre ».
 *
 * Accessibilité (socle RGAA) : lien d'évitement, landmarks, onglets au clavier
 * (flèches, Origine, Fin), formulaires étiquetés, régions `aria-live` pour les
 * mises à jour asynchrones, couleur toujours doublée d'un texte.
 */
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, Bbox, Eda as EdaData, Filtres, Kpi, Troncon, Ville } from "./api";
import { Eda } from "./Eda";
import { Fiche } from "./Fiche";
import { Legende } from "./Legende";
import { DEC, EUR, NB, NOTES } from "./notes";
import { Scenario } from "./Scenario";
import { Tableau } from "./Tableau";

const ONGLETS = [
  { cle: "carte", libelle: "Carte" },
  { cle: "eda", libelle: "EDA" },
  { cle: "tableau", libelle: "Tableau" },
  { cle: "scenario", libelle: "Scénario" },
] as const;

type CleOnglet = (typeof ONGLETS)[number]["cle"];

// MapLibre pèse à lui seul l'essentiel du bundle. En chargement différé, l'en-tête,
// les filtres et les indicateurs s'affichent sans l'attendre, et les onglets EDA,
// Tableau et Scénario n'en ont jamais besoin.
const Carte = lazy(() => import("./Carte").then((m) => ({ default: m.Carte })));

const ANNEES_POSE = [
  { valeur: 2100, libelle: "Toutes années" },
  { valeur: 1950, libelle: "Avant 1950" },
  { valeur: 1970, libelle: "Avant 1970" },
  { valeur: 1990, libelle: "Avant 1990" },
];

const MESSAGE_ERREUR =
  "Les données ne sont pas accessibles pour l'instant. L'instance de démonstration " +
  "s'arrête après quelques minutes sans visite : rechargez la page dans une minute.";

export default function App() {
  const [villes, setVilles] = useState<Ville[]>([]);
  const [materiaux, setMateriaux] = useState<string[]>([]);
  const [filtres, setFiltres] = useState<Filtres | null>(null);

  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [troncons, setTroncons] = useState<Troncon[]>([]);
  const [eda, setEda] = useState<EdaData | null>(null);
  const [geo, setGeo] = useState<GeoJSON.FeatureCollection | null>(null);

  const [onglet, setOnglet] = useState<CleOnglet>("carte");
  const [selection, setSelection] = useState<string | null>(null);
  const [recentrage, setRecentrage] = useState(0);
  const [detail, setDetail] = useState<Troncon | null>(null);
  const [modeDessin, setModeDessin] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const signaler = useCallback((e: unknown) => {
    if (e instanceof DOMException && e.name === "AbortError") return;
    console.error(e);
    setErreur(MESSAGE_ERREUR);
  }, []);

  /* Villes disponibles : détermine le périmètre initial. */
  useEffect(() => {
    const ctrl = new AbortController();
    api
      .villes(ctrl.signal)
      .then((v) => {
        setVilles(v);
        if (v.length) {
          setFiltres({ ville: v[0].cle, notes: [4, 5], materiau: "", poseMax: 2100, bbox: null });
        }
      })
      .catch(signaler);
    return () => ctrl.abort();
  }, [signaler]);

  const ville = filtres?.ville;

  /* Matériaux réellement présents dans la ville : le filtre n'invente rien. */
  useEffect(() => {
    if (!ville) return;
    const ctrl = new AbortController();
    api.materiaux(ville, ctrl.signal).then(setMateriaux).catch(signaler);
    return () => ctrl.abort();
  }, [ville, signaler]);

  /* Les quatre lectures du périmètre, rechargées ensemble. */
  useEffect(() => {
    if (!filtres) return;
    const ctrl = new AbortController();
    setErreur(null);
    Promise.all([
      api.kpi(filtres, ctrl.signal).then(setKpi),
      api.troncons(filtres, 300, ctrl.signal).then(setTroncons),
      api.eda(filtres, ctrl.signal).then(setEda),
      api.geojson(filtres, ctrl.signal).then(setGeo),
    ]).catch(signaler);
    return () => ctrl.abort();
  }, [filtres, signaler]);

  /* Fiche du tronçon sélectionné : requête unitaire, car la carte affiche tout
     le périmètre alors que le tableau est plafonné à 300 lignes. */
  useEffect(() => {
    if (!ville || !selection) {
      setDetail(null);
      return;
    }
    const ctrl = new AbortController();
    api.troncon(ville, selection, ctrl.signal).then(setDetail).catch(signaler);
    return () => ctrl.abort();
  }, [ville, selection, signaler]);

  const majFiltres = (patch: Partial<Filtres>) =>
    setFiltres((f) => (f ? { ...f, ...patch } : f));

  const changerVille = (cle: string) => {
    setSelection(null);
    setModeDessin(false);
    majFiltres({ ville: cle, bbox: null });
  };

  const basculerNote = (n: number) => {
    if (!filtres) return;
    const actives = filtres.notes.includes(n)
      ? filtres.notes.filter((x) => x !== n)
      : [...filtres.notes, n];
    if (actives.length) majFiltres({ notes: actives.sort() });
  };

  const surEmprise = (b: Bbox | null) => {
    setModeDessin(false);
    majFiltres({ bbox: b });
  };

  const villeCourante = useMemo(
    () => villes.find((v) => v.cle === filtres?.ville) ?? null,
    [villes, filtres?.ville],
  );

  /* Sélectionner depuis le tableau ramène sur la carte ET s'y rend : sans
     recentrage, le tronçon surligné serait hors écran neuf fois sur dix. */
  const selectionner = (id: string) => {
    setSelection(id);
    setOnglet("carte");
    setRecentrage((n) => n + 1);
  };

  if (!filtres) {
    return (
      <>
        <Entete />
        <main id="contenu">
          {erreur ? (
            <p role="alert" className="erreur">
              {erreur}
            </p>
          ) : (
            <p role="status" className="vide">
              Chargement. Le premier affichage peut demander une minute, le temps que
              l&apos;instance de démonstration redémarre.
            </p>
          )}
        </main>
      </>
    );
  }

  return (
    <>
      <a className="evitement" href="#contenu">
        Aller au contenu principal
      </a>
      <Entete />

      <div className="barre">
        <div className="champ">
          <label htmlFor="ville">Ville</label>
          <select id="ville" value={filtres.ville} onChange={(e) => changerVille(e.target.value)}>
            {villes.map((v) => (
              <option key={v.cle} value={v.cle}>
                {v.nom}
              </option>
            ))}
          </select>
        </div>

        <div className="champ">
          <label htmlFor="note-min">Note minimale</label>
          <select
            id="note-min"
            value={Math.min(...filtres.notes)}
            onChange={(e) =>
              majFiltres({ notes: NOTES.filter((n) => n >= Number(e.target.value)) })
            }
          >
            {NOTES.map((n) => (
              <option key={n} value={n}>
                {n} et plus
              </option>
            ))}
          </select>
        </div>

        <div className="champ">
          <label htmlFor="materiau">Matériau</label>
          <select
            id="materiau"
            value={filtres.materiau}
            onChange={(e) => majFiltres({ materiau: e.target.value })}
          >
            <option value="">Tous</option>
            {materiaux.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="champ">
          <label htmlFor="pose-max">Année de pose</label>
          <select
            id="pose-max"
            value={filtres.poseMax}
            onChange={(e) => majFiltres({ poseMax: Number(e.target.value) })}
          >
            {ANNEES_POSE.map((a) => (
              <option key={a.valeur} value={a.valeur}>
                {a.libelle}
              </option>
            ))}
          </select>
        </div>

        <div className="champ">
          <span className="etiquette" id="etiquette-emprise">
            Emprise
          </span>
          <div className="groupe-boutons" role="group" aria-labelledby="etiquette-emprise">
            <button
              type="button"
              className="secondaire"
              aria-pressed={modeDessin}
              onClick={() => {
                setOnglet("carte");
                setModeDessin(!modeDessin);
              }}
            >
              Dessiner une zone
            </button>
            {filtres.bbox && (
              <button type="button" className="secondaire" onClick={() => surEmprise(null)}>
                Effacer
              </button>
            )}
          </div>
        </div>
      </div>

      {erreur && (
        <p role="alert" className="erreur bandeau">
          {erreur}
        </p>
      )}

      <dl className="kpi" aria-live="polite">
        <Indicateur libelle="Linéaire filtré" valeur={kpi ? `${DEC.format(kpi.lineaire_km)} km` : null} />
        <Indicateur libelle="Tronçons" valeur={kpi ? NB.format(kpi.nb_troncons) : null} />
        <Indicateur
          libelle="Linéaire note 5"
          valeur={kpi ? `${DEC.format(kpi.lineaire_note5_km)} km` : null}
        />
        <Indicateur libelle="Âge moyen" valeur={kpi ? `${DEC.format(kpi.age_moyen_ans)} ans` : null} />
        <Indicateur
          libelle="Casses attendues 3 ans"
          valeur={kpi ? DEC.format(kpi.casses_attendues_h3) : null}
        />
        <Indicateur
          libelle="Coût de renouvellement"
          valeur={kpi ? EUR.format(kpi.cout_renouvellement_euros) : null}
        />
      </dl>

      <Onglets actif={onglet} onChange={setOnglet} />

      <main id="contenu">
        <section
          className={`panneau ${onglet === "carte" ? "actif" : ""}`}
          id="p-carte"
          role="tabpanel"
          aria-labelledby="tab-carte"
          hidden={onglet !== "carte"}
        >
          <Suspense fallback={<div className="carte carte-attente" role="status">Chargement de la carte.</div>}>
            <Carte
              ville={villeCourante}
              geo={geo}
              selection={selection}
              onSelection={setSelection}
              recentrage={recentrage}
              visible={onglet === "carte"}
              modeDessin={modeDessin}
              emprise={filtres.bbox}
              onEmprise={surEmprise}
            />
          </Suspense>
          <aside className="lateral">
            <h2>Note patrimoniale</h2>
            <Legende
              comptes={eda?.notes ?? []}
              actives={filtres.notes}
              onBascule={basculerNote}
            />
            <h2>Tronçon sélectionné</h2>
            <div aria-live="polite">
              <Fiche troncon={detail} />
            </div>
          </aside>
        </section>

        <section
          className={`panneau defilant ${onglet === "eda" ? "actif" : ""}`}
          id="p-eda"
          role="tabpanel"
          aria-labelledby="tab-eda"
          hidden={onglet !== "eda"}
        >
          <h2 className="sr-only">Exploration du périmètre</h2>
          {eda ? <Eda eda={eda} /> : <p className="vide">Chargement des agrégats.</p>}
        </section>

        <section
          className={`panneau defilant ${onglet === "tableau" ? "actif" : ""}`}
          id="p-tableau"
          role="tabpanel"
          aria-labelledby="tab-tableau"
          hidden={onglet !== "tableau"}
        >
          <h2 className="sr-only">Tronçons du périmètre</h2>
          <Tableau troncons={troncons} selection={selection} onSelection={selectionner} />
        </section>

        <section
          className={`panneau defilant ${onglet === "scenario" ? "actif" : ""}`}
          id="p-scenario"
          role="tabpanel"
          aria-labelledby="tab-scenario"
          hidden={onglet !== "scenario"}
        >
          <h2 className="sr-only">Scénario de renouvellement</h2>
          <Scenario filtres={filtres} />
        </section>
      </main>

      <footer>
        <p>
          Démonstration publique. Le réseau est fictif, généré par simulation et posé sur le fond
          de carte réel de la ville : aucune donnée de réseau réelle n&apos;est utilisée. Code sous
          licence MIT.
        </p>
      </footer>
    </>
  );
}

function Entete() {
  return (
    <header role="banner">
      <h1>
        Renov.ia <span className="badge-demo">démo, données synthétiques</span>
      </h1>
      <p>Priorisation du renouvellement des canalisations d&apos;eau potable</p>
    </header>
  );
}

function Indicateur({ libelle, valeur }: { libelle: string; valeur: string | null }) {
  return (
    <div>
      <dt>{libelle}</dt>
      <dd>{valeur ?? <span className="squelette" />}</dd>
    </div>
  );
}

/**
 * Onglets au clavier : flèches pour se déplacer, Origine et Fin pour les
 * extrémités, un seul onglet dans l'ordre de tabulation (motif ARIA
 * « tabs with automatic activation »).
 */
function Onglets({ actif, onChange }: { actif: CleOnglet; onChange: (c: CleOnglet) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const auClavier = (e: React.KeyboardEvent, index: number) => {
    const dernier = ONGLETS.length - 1;
    const cible =
      e.key === "ArrowRight" ? (index === dernier ? 0 : index + 1)
      : e.key === "ArrowLeft" ? (index === 0 ? dernier : index - 1)
      : e.key === "Home" ? 0
      : e.key === "End" ? dernier
      : null;
    if (cible === null) return;
    e.preventDefault();
    onChange(ONGLETS[cible].cle);
    refs.current[cible]?.focus();
  };

  return (
    <div className="onglets" role="tablist" aria-label="Vues du périmètre">
      {ONGLETS.map((o, i) => (
        <button
          key={o.cle}
          ref={(el) => (refs.current[i] = el)}
          role="tab"
          id={`tab-${o.cle}`}
          aria-controls={`p-${o.cle}`}
          aria-selected={actif === o.cle}
          tabIndex={actif === o.cle ? 0 : -1}
          onClick={() => onChange(o.cle)}
          onKeyDown={(e) => auClavier(e, i)}
        >
          {o.libelle}
        </button>
      ))}
    </div>
  );
}
