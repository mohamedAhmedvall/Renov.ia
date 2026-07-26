/** Fiche du tronçon sélectionné, sur la carte ou depuis le tableau. */

import { ANNEE_REFERENCE, Troncon } from "./api";
import { DEC, EUR, LIBELLE_NOTE, NB, PCT } from "./notes";
import { NoteBadge } from "./NoteBadge";

export function Fiche({ troncon }: { troncon: Troncon | null }) {
  if (!troncon) {
    return (
      <p className="vide">
        Sélectionnez un tronçon sur la carte, ou depuis l&apos;onglet Tableau au clavier.
      </p>
    );
  }
  const t = troncon;
  const age = ANNEE_REFERENCE - t.annee_pose;

  return (
    <dl className="fiche">
      <dt>Identifiant</dt>
      <dd>{t.id_troncon}</dd>

      <dt>Note patrimoniale</dt>
      <dd>
        <NoteBadge note={t.note_h3} />{" "}
        {t.note_h3 != null ? LIBELLE_NOTE[t.note_h3] : "non scoré"}
      </dd>

      <dt>Matériau</dt>
      <dd>{t.materiau}</dd>

      <dt>Diamètre</dt>
      <dd>{t.diametre_mm} mm</dd>

      <dt>Longueur</dt>
      <dd>{NB.format(Math.round(t.longueur_m))} m</dd>

      <dt>Année de pose</dt>
      <dd>
        {t.annee_pose} ({age} ans)
      </dd>

      <dt>Typologie</dt>
      <dd>{t.typologie}</dd>

      <dt>Population desservie</dt>
      <dd>{NB.format(t.population_desservie)}</dd>

      <dt>Conséquence</dt>
      <dd>{DEC.format(t.consequence)} sur 1</dd>

      <dt>Casses sur 10 ans</dt>
      <dd>{t.casses_10ans}</dd>

      <dt>P(casse) 3 ans</dt>
      <dd>{t.score_h3 != null ? PCT.format(t.score_h3) : "n.d."}</dd>

      <dt>Coût de renouvellement</dt>
      <dd>{EUR.format(t.cout_renouvellement_euros)}</dd>
    </dl>
  );
}
