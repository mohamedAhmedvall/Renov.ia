/**
 * Onglet Tableau : le périmètre filtré, trié par risque décroissant.
 *
 * C'est l'équivalent accessible de la carte. La sélection passe par un vrai
 * bouton dans l'en-tête de ligne (RGAA 7.1 : tout composant d'interface doit
 * être utilisable au clavier), pas par un `onClick` posé sur `<tr>`.
 */
import { Troncon } from "./api";
import { NB, PCT } from "./notes";
import { NoteBadge } from "./NoteBadge";

interface Props {
  troncons: Troncon[];
  selection: string | null;
  onSelection: (id: string) => void;
}

export function Tableau({ troncons, selection, onSelection }: Props) {
  if (!troncons.length) {
    return (
      <p className="vide">
        Aucun tronçon dans le périmètre courant. Élargissez les notes retenues ou effacez
        l&apos;emprise dessinée.
      </p>
    );
  }

  return (
    <table>
      <caption className="sr-only">
        Tronçons du périmètre filtré, triés par probabilité de casse à 3 ans décroissante.
        Activez l&apos;identifiant d&apos;une ligne pour afficher sa fiche sur la carte.
      </caption>
      <thead>
        <tr>
          <th scope="col">Tronçon</th>
          <th scope="col">Matériau</th>
          <th scope="col">Ø (mm)</th>
          <th scope="col">Longueur (m)</th>
          <th scope="col">Pose</th>
          <th scope="col">Casses 10 ans</th>
          <th scope="col">P(casse) 3 ans</th>
          <th scope="col">Note</th>
        </tr>
      </thead>
      <tbody>
        {troncons.map((t) => (
          <tr key={t.id_troncon} aria-selected={t.id_troncon === selection}>
            <th scope="row">
              <button type="button" className="lien-troncon" onClick={() => onSelection(t.id_troncon)}>
                {t.id_troncon}
              </button>
            </th>
            <td>{t.materiau}</td>
            <td className="num">{t.diametre_mm}</td>
            <td className="num">{NB.format(Math.round(t.longueur_m))}</td>
            <td className="num">{t.annee_pose}</td>
            <td className="num">{t.casses_10ans}</td>
            <td className="num">
              {t.score_h3 != null ? PCT.format(t.score_h3) : "n.d."}
            </td>
            <td>
              <NoteBadge note={t.note_h3} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
