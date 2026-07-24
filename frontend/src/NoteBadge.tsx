/** Note patrimoniale 1–5 : couleur TOUJOURS doublée du chiffre (RGAA 3.2). */

const LIBELLES: Record<number, string> = {
  1: "note 1 — risque faible",
  2: "note 2 — risque modéré",
  3: "note 3 — à surveiller",
  4: "note 4 — prioritaire",
  5: "note 5 — critique",
};

export function NoteBadge({ note }: { note: number | null }) {
  if (note == null) return <span>—</span>;
  return (
    <span className={`note note-${note}`} aria-label={LIBELLES[note] ?? `note ${note}`}>
      {note}
    </span>
  );
}
