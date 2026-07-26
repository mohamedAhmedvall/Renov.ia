/**
 * Primitives de graphiques en SVG natif.
 *
 * Pas de librairie de dataviz : trois formes suffisent ici (barres, colonnes,
 * courbe cumulée) et un SVG écrit à la main reste inspectable, sans dépendance
 * ni bundle supplémentaire. Chaque graphique porte un `aria-label` qui énonce
 * ce que la forme montre, pour que l'information ne repose pas sur le visuel.
 */
import { Serie } from "./api";
import { NB } from "./notes";

const L = 460;
const H = 240;
const ACCENT = "#00676c";
const AXE = "#d5d2ca";
const TEXTE = "#4a5c66";

interface BarresProps {
  donnees: Serie[];
  couleurs?: Record<string, string>;
  formatValeur?: (v: number) => string;
  ariaLabel: string;
}

/** Barres horizontales : adapté aux catégories dont le libellé est long. */
export function Barres({ donnees, couleurs, formatValeur, ariaLabel }: BarresProps) {
  const gauche = 104;
  const droite = 46;
  const max = Math.max(1, ...donnees.map((d) => d.valeur));
  const hauteur = (H - 32) / Math.max(donnees.length, 1);

  return (
    <svg viewBox={`0 0 ${L} ${H}`} role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      {donnees.map((d, i) => {
        const y = 10 + i * hauteur;
        const largeur = ((L - gauche - droite) * d.valeur) / max;
        return (
          <g key={d.cle}>
            <rect
              x={gauche}
              y={y + hauteur * 0.16}
              width={Math.max(largeur, 1)}
              height={hauteur * 0.68}
              fill={couleurs?.[d.cle] ?? ACCENT}
              rx={2}
            />
            <text x={gauche - 8} y={y + hauteur * 0.62} fontSize={11} fill={TEXTE} textAnchor="end">
              {d.cle}
            </text>
            <text
              x={gauche + largeur + 6}
              y={y + hauteur * 0.62}
              fontSize={11}
              fill="#1c2b33"
              fontWeight={600}
            >
              {formatValeur ? formatValeur(d.valeur) : NB.format(Math.round(d.valeur))}
            </text>
          </g>
        );
      })}
      <line x1={gauche} y1={8} x2={gauche} y2={H - 18} stroke={AXE} />
    </svg>
  );
}

interface ColonnesProps {
  donnees: Serie[];
  legendeX: string;
  ariaLabel: string;
}

/** Colonnes verticales : adapté aux séries ordonnées (décennies, années). */
export function Colonnes({ donnees, legendeX, ariaLabel }: ColonnesProps) {
  const gauche = 44;
  const bas = 36;
  const max = Math.max(1, ...donnees.map((d) => d.valeur));
  const largeur = (L - gauche - 10) / Math.max(donnees.length, 1);
  // Au-delà de 8 colonnes, une étiquette sur deux (ou sur trois) évite le chevauchement.
  const pas = Math.ceil(donnees.length / 8);

  return (
    <svg viewBox={`0 0 ${L} ${H}`} role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      <line x1={gauche} y1={H - bas} x2={L - 10} y2={H - bas} stroke={AXE} />
      <line x1={gauche} y1={14} x2={gauche} y2={H - bas} stroke={AXE} />
      {donnees.map((d, i) => {
        const hauteur = ((H - bas - 14) * d.valeur) / max;
        const x = gauche + i * largeur;
        return (
          <g key={d.cle}>
            <rect
              x={x + largeur * 0.15}
              y={H - bas - hauteur}
              width={largeur * 0.7}
              height={Math.max(hauteur, 0.5)}
              fill={ACCENT}
              rx={2}
            />
            {i % pas === 0 && (
              <text x={x + largeur / 2} y={H - bas + 14} fontSize={10} fill={TEXTE} textAnchor="middle">
                {d.cle}
              </text>
            )}
          </g>
        );
      })}
      <text x={gauche - 6} y={18} fontSize={10} fill={TEXTE} textAnchor="end">
        {NB.format(Math.round(max))}
      </text>
      <text x={gauche - 6} y={H - bas} fontSize={10} fill={TEXTE} textAnchor="end">
        0
      </text>
      <text x={gauche} y={H - 6} fontSize={10} fill={TEXTE}>
        {legendeX}
      </text>
    </svg>
  );
}

interface CourbeProps {
  points: { x: number; y: number }[];
  annotation: string;
  ariaLabel: string;
}

/** Courbe cumulée avec diagonale de référence (priorisation aléatoire). */
export function Courbe({ points, annotation, ariaLabel }: CourbeProps) {
  const gauche = 44;
  const bas = 36;
  const px = (p: { x: number }) => gauche + p.x * (L - gauche - 12);
  const py = (p: { y: number }) => H - bas - p.y * (H - bas - 14);
  const trace = points.map((p, i) => `${i ? "L" : "M"}${px(p).toFixed(1)},${py(p).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${L} ${H}`} role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      <line x1={gauche} y1={H - bas} x2={L - 12} y2={H - bas} stroke={AXE} />
      <line x1={gauche} y1={14} x2={gauche} y2={H - bas} stroke={AXE} />
      <line x1={gauche} y1={H - bas} x2={L - 12} y2={14} stroke="#b9b5ac" strokeDasharray="4 4" />
      <path d={trace} fill="none" stroke={ACCENT} strokeWidth={2.5} />
      <text x={gauche + 4} y={26} fontSize={11} fill="#1c2b33" fontWeight={600}>
        {annotation}
      </text>
      <text x={L - 12} y={H - bas + 14} fontSize={10} fill={TEXTE} textAnchor="end">
        100 % du linéaire
      </text>
      <text x={gauche} y={H - 6} fontSize={10} fill={TEXTE}>
        diagonale = priorisation aléatoire
      </text>
    </svg>
  );
}
