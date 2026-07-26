/** Note patrimoniale 1–5 : couleur TOUJOURS doublée du chiffre (RGAA 3.2). */

import { LIBELLE_NOTE } from "./notes";

export function NoteBadge({ note }: { note: number | null }) {
  // « n.d. » plutôt qu'un tiret : les lecteurs d'écran annoncent les tirets de
  // façon très variable, du silence à « trait d'union ».
  if (note == null) return <span>n.d.</span>;
  return (
    <span className={`note note-${note}`} aria-label={`note ${note}, ${LIBELLE_NOTE[note] ?? ""}`}>
      {note}
    </span>
  );
}
