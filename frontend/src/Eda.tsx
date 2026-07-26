/**
 * Onglet EDA : six lectures du périmètre filtré.
 *
 * Les agrégats viennent du serveur (`/api/eda`) et non d'un calcul dans le
 * navigateur : le front n'a jamais à télécharger les milliers de tronçons ni
 * l'historique de casses pour dessiner ces graphiques, et les chiffres
 * affichés sont exactement ceux du domaine.
 */
import { Eda as EdaData, Serie } from "./api";
import { Barres, Colonnes, Courbe } from "./graphiques";
import { COULEUR_NOTE, DEC, LIBELLE_NOTE, NB } from "./notes";

/** Les deux premières valeurs d'une série, pour résumer un graphique à l'oral. */
function tete(donnees: Serie[], unite = ""): string {
  if (!donnees.length) return "aucune donnée";
  return donnees
    .slice(0, 2)
    .map((d) => `${d.cle} ${DEC.format(d.valeur)}${unite}`)
    .join(", ");
}

function Bloc({ titre, sous, children }: { titre: string; sous: string; children: React.ReactNode }) {
  return (
    <div className="carte-graph">
      <h3>{titre}</h3>
      <p>{sous}</p>
      {children}
    </div>
  );
}

export function Eda({ eda }: { eda: EdaData }) {
  if (!eda.nb_troncons) {
    return (
      <p className="vide">
        Aucun tronçon dans le périmètre courant. Élargissez les notes retenues ou effacez
        l&apos;emprise dessinée.
      </p>
    );
  }

  const notes = eda.notes.map((s) => ({ cle: `Note ${s.cle}`, valeur: s.valeur }));
  const couleursNotes = Object.fromEntries(
    eda.notes.map((s) => [`Note ${s.cle}`, COULEUR_NOTE[Number(s.cle)]]),
  );
  const dominante = [...eda.notes].sort((a, b) => b.valeur - a.valeur)[0];

  return (
    <div className="grille">
      <Bloc titre="Distribution des notes" sous="répartition du périmètre avant filtre de note">
        <Barres
          donnees={notes}
          couleurs={couleursNotes}
          ariaLabel={
            `Répartition des ${NB.format(eda.nb_troncons)} tronçons par note. ` +
            `La note ${dominante.cle} (${LIBELLE_NOTE[Number(dominante.cle)]}) domine avec ` +
            `${NB.format(dominante.valeur)} tronçons.`
          }
        />
      </Bloc>

      <Bloc titre="Casses observées par matériau" sous="historique simulé sur 20 ans">
        <Barres
          donnees={eda.casses_par_materiau}
          ariaLabel={`Casses cumulées par matériau. En tête : ${tete(eda.casses_par_materiau)}.`}
        />
      </Bloc>

      <Bloc titre="Âge du patrimoine" sous="nombre de tronçons par décennie de pose">
        <Colonnes
          donnees={eda.poses_par_decennie}
          legendeX="décennie de pose"
          ariaLabel={
            "Répartition des poses par décennie, de " +
            `${eda.poses_par_decennie[0]?.cle ?? "?"} à ` +
            `${eda.poses_par_decennie.at(-1)?.cle ?? "?"}.`
          }
        />
      </Bloc>

      <Bloc titre="Linéaire par matériau" sous="kilomètres posés">
        <Barres
          donnees={eda.lineaire_par_materiau_km}
          formatValeur={(v) => `${DEC.format(v)} km`}
          ariaLabel={`Linéaire par matériau. En tête : ${tete(eda.lineaire_par_materiau_km, " km")}.`}
        />
      </Bloc>

      <Bloc titre="Courbe de capture" sous="casses captées en priorisant par risque au mètre">
        <Courbe
          points={eda.courbe_capture}
          annotation={`capture @ 20 % = ${(eda.capture_20pct * 100).toFixed(0)} %`}
          ariaLabel={
            `En renouvelant les 20 % de linéaire les plus risqués, on couvre ` +
            `${(eda.capture_20pct * 100).toFixed(0)} % des casses observées, contre 20 % ` +
            "pour une priorisation aléatoire."
          }
        />
      </Bloc>

      <Bloc titre="Casses par année" sous="sur les dix dernières années du périmètre">
        <Colonnes
          donnees={eda.casses_par_annee}
          legendeX="année"
          ariaLabel={
            "Casses constatées par année sur le périmètre filtré, total " +
            `${NB.format(eda.casses_par_annee.reduce((s, d) => s + d.valeur, 0))} casses.`
          }
        />
      </Bloc>
    </div>
  );
}
