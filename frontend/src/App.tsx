/**
 * Écran unique de démonstration : KPI réseau, carte des tronçons colorés par
 * Note 1–5, tableau priorisé, simulateur de scénario budgétaire.
 *
 * Accessibilité (socle RGAA) : lien d'évitement, landmarks (banner/main),
 * hiérarchie de titres, formulaires étiquetés, tableau avec scope, couleurs
 * doublées d'un texte (la note est toujours affichée en chiffres), focus
 * visible, contrastes AA.
 */
import { useEffect, useState } from "react";

import { api, Kpi, Scenario, Troncon } from "./api";
import { Carte } from "./Carte";
import { NoteBadge } from "./NoteBadge";

const EUR = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

export default function App() {
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [troncons, setTroncons] = useState<Troncon[]>([]);
  const [noteMin, setNoteMin] = useState(4);
  const [budget, setBudget] = useState(2_000_000);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api.kpi().then(setKpi).catch((e) => setErreur(String(e)));
  }, []);
  useEffect(() => {
    api.troncons(noteMin).then(setTroncons).catch((e) => setErreur(String(e)));
  }, [noteMin]);

  const lancerScenario = (ev: React.FormEvent) => {
    ev.preventDefault();
    setScenario(null);
    api.optimiser(budget).then(setScenario).catch((e) => setErreur(String(e)));
  };

  return (
    <>
      <a className="evitement" href="#contenu">Aller au contenu principal</a>
      <header role="banner">
        <h1>Renov.ia <span className="badge-demo">démo — données synthétiques</span></h1>
        <p>Priorisation du renouvellement des canalisations d&apos;eau potable</p>
      </header>

      <main id="contenu">
        {erreur && <p role="alert" className="erreur">{erreur}</p>}

        <section aria-labelledby="titre-kpi">
          <h2 id="titre-kpi">Réseau</h2>
          {kpi && (
            <dl className="kpi">
              <div><dt>Linéaire total</dt><dd>{kpi.lineaire_total_km} km</dd></div>
              <div><dt>Linéaire en note 5</dt><dd>{kpi.lineaire_note5_km} km</dd></div>
              <div><dt>Tronçons</dt><dd>{kpi.nb_troncons.toLocaleString("fr-FR")}</dd></div>
              <div><dt>Âge moyen</dt><dd>{kpi.age_moyen_ans} ans</dd></div>
            </dl>
          )}
        </section>

        <section aria-labelledby="titre-carte">
          <h2 id="titre-carte">Carte du risque</h2>
          <label htmlFor="note-min">Note patrimoniale minimale affichée</label>{" "}
          <select id="note-min" value={noteMin} onChange={(e) => setNoteMin(Number(e.target.value))}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n} et plus</option>
            ))}
          </select>
          <Carte noteMin={noteMin} />
        </section>

        <section aria-labelledby="titre-tableau">
          <h2 id="titre-tableau">Tronçons prioritaires (note ≥ {noteMin})</h2>
          <table>
            <caption className="sr-only">
              Tronçons triés par probabilité de casse à 3 ans décroissante
            </caption>
            <thead>
              <tr>
                <th scope="col">Tronçon</th>
                <th scope="col">Matériau</th>
                <th scope="col">Ø (mm)</th>
                <th scope="col">Pose</th>
                <th scope="col">P(casse) 3 ans</th>
                <th scope="col">Note</th>
              </tr>
            </thead>
            <tbody>
              {troncons.slice(0, 15).map((t) => (
                <tr key={t.id_troncon}>
                  <th scope="row">{t.id_troncon}</th>
                  <td>{t.materiau}</td>
                  <td className="num">{t.diametre_mm}</td>
                  <td className="num">{t.annee_pose}</td>
                  <td className="num">{t.score_h3 != null ? `${(t.score_h3 * 100).toFixed(1)} %` : "—"}</td>
                  <td><NoteBadge note={t.note_h3} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="titre-optimiseur">
          <h2 id="titre-optimiseur">Scénario de renouvellement</h2>
          <form onSubmit={lancerScenario}>
            <label htmlFor="budget">Budget (€)</label>{" "}
            <input
              id="budget"
              type="number"
              min={100000}
              step={100000}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
            />{" "}
            <button type="submit">Calculer le scénario</button>
          </form>
          {scenario && (
            <p aria-live="polite">
              Avec {EUR.format(scenario.budget)} : <strong>{scenario.nb_troncons} tronçons</strong> renouvelés
              ({scenario.lineaire_km} km) pour {EUR.format(scenario.cout_total)}, soit{" "}
              <strong>
                {scenario.casses_evitees} casses évitées attendues (± {scenario.casses_evitees_ic95})
              </strong>{" "}
              sur {scenario.horizon} ans.
            </p>
          )}
        </section>
      </main>

      <footer>
        <p>
          Démonstration publique — réseau fictif généré par simulation (aucune donnée réelle).
          Code sous licence MIT.
        </p>
      </footer>
    </>
  );
}
