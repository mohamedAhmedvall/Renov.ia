/**
 * Légende des notes, cliquable : chaque entrée est un filtre d'affichage.
 *
 * Les comptes décrivent le périmètre AVANT filtre de note (cf. `/api/eda`),
 * sinon une note décochée afficherait zéro et on ne saurait plus ce qu'on
 * masque. La dernière note active ne peut pas être décochée : une carte vide
 * ne serait pas un état utile, seulement un cul-de-sac.
 */
import { Serie } from "./api";
import { COULEUR_NOTE, LIBELLE_NOTE, NB, NOTES } from "./notes";

interface Props {
  comptes: Serie[];
  actives: number[];
  onBascule: (note: number) => void;
}

export function Legende({ comptes, actives, onBascule }: Props) {
  const compte = (n: number) => comptes.find((s) => s.cle === String(n))?.valeur ?? 0;
  const derniere = actives.length === 1;

  return (
    <ul className="legende">
      {[...NOTES].reverse().map((n) => {
        const active = actives.includes(n);
        return (
          <li key={n}>
            <button
              type="button"
              aria-pressed={active}
              disabled={active && derniere}
              onClick={() => onBascule(n)}
            >
              <span className="puce" style={{ background: COULEUR_NOTE[n] }} aria-hidden="true" />
              <span className="libelle">
                <strong>{n}</strong> {LIBELLE_NOTE[n]}
              </span>
              <span className="compte">{NB.format(compte(n))}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
