/**
 * Onglet Scénario : arbitrage budgétaire sur le périmètre filtré.
 *
 * Cet onglet ne figure pas dans la maquette de la vue tronçons, mais il porte
 * l'optimiseur sous contrainte de budget (`optimizer/`), qui est une des deux
 * briques de décision du produit. Le supprimer aurait retiré une fonction
 * existante ; il est repris ici dans la grammaire de la maquette, en onglet.
 *
 * Il travaille sur le MÊME périmètre que les trois autres onglets : dessiner
 * une emprise puis calculer un scénario répond à « que faire de ce quartier
 * avec 2 M€ ».
 */
import { useState } from "react";

import { api, Filtres, Scenario as ScenarioData } from "./api";
import { DEC, EUR, NB } from "./notes";

export function Scenario({ filtres }: { filtres: Filtres }) {
  const [budget, setBudget] = useState(2_000_000);
  const [horizon, setHorizon] = useState(3);
  const [scenario, setScenario] = useState<ScenarioData | null>(null);
  const [calcul, setCalcul] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const lancer = (ev: React.FormEvent) => {
    ev.preventDefault();
    setCalcul(true);
    setErreur(null);
    setScenario(null);
    api
      .optimiser(filtres, budget, horizon)
      .then(setScenario)
      .catch((e) => {
        console.error(e);
        setErreur("Le scénario n'a pas pu être calculé. Réessayez dans un instant.");
      })
      .finally(() => setCalcul(false));
  };

  return (
    <div className="scenario">
      <form onSubmit={lancer}>
        <div className="champ">
          <label htmlFor="budget">Budget (€)</label>
          <input
            id="budget"
            type="number"
            min={100000}
            step={100000}
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </div>
        <div className="champ">
          <label htmlFor="horizon">Horizon de risque</label>
          <select id="horizon" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={1}>1 an</option>
            <option value={3}>3 ans</option>
            <option value={5}>5 ans</option>
          </select>
        </div>
        <button type="submit" disabled={calcul}>
          {calcul ? "Calcul en cours" : "Calculer le scénario"}
        </button>
      </form>

      <div aria-live="polite">
        {erreur && (
          <p role="alert" className="erreur">
            {erreur}
          </p>
        )}

        {scenario && scenario.nb_troncons === 0 && (
          <p className="vide">
            Aucun tronçon éligible dans ce périmètre avec ce budget. Élargissez les filtres ou
            augmentez le budget.
          </p>
        )}

        {scenario && scenario.nb_troncons > 0 && (
          <>
            <dl className="kpi kpi-scenario">
              <div>
                <dt>Tronçons retenus</dt>
                <dd>{NB.format(scenario.nb_troncons)}</dd>
              </div>
              <div>
                <dt>Linéaire renouvelé</dt>
                <dd>{DEC.format(scenario.lineaire_km)} km</dd>
              </div>
              <div>
                <dt>Coût engagé</dt>
                <dd>{EUR.format(scenario.cout_total)}</dd>
              </div>
              <div>
                <dt>Casses évitées</dt>
                <dd>
                  {DEC.format(scenario.casses_evitees)}{" "}
                  <span className="ic95">± {DEC.format(scenario.casses_evitees_ic95)}</span>
                </dd>
              </div>
            </dl>
            <p className="lecture">
              Avec {EUR.format(scenario.budget)}, l&apos;optimiseur retient{" "}
              {NB.format(scenario.nb_troncons)} tronçons ({DEC.format(scenario.lineaire_km)} km) pour{" "}
              {EUR.format(scenario.cout_total)}, soit {DEC.format(scenario.casses_evitees)} casses
              évitées attendues (± {DEC.format(scenario.casses_evitees_ic95)}, intervalle de
              confiance à 95 %) sur {scenario.horizon} ans.
            </p>
          </>
        )}

        {!scenario && !erreur && !calcul && (
          <p className="vide">
            Le calcul porte sur le périmètre filtré : dessinez une emprise sur la carte pour
            arbitrer quartier par quartier.
          </p>
        )}
      </div>
    </div>
  );
}
