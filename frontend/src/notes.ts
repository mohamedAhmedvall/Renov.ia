/**
 * Échelle de Note patrimoniale 1–5, partagée par la carte, la légende, le
 * tableau et les graphiques.
 *
 * UNE seule palette pour toute l'application : une pastille de légende doit
 * avoir exactement la couleur du tracé qu'elle désigne. Ces teintes sont
 * celles qui portent du texte blanc en contraste AA dans les badges ; sur le
 * fond de carte, elles sont doublées d'un liseré blanc (cf. Carte.tsx) plutôt
 * que remplacées par des couleurs plus vives, qui casseraient la
 * correspondance.
 */

export const NOTES = [1, 2, 3, 4, 5] as const;

export const COULEUR_NOTE: Record<number, string> = {
  1: "#2e7d32",
  2: "#797822",
  3: "#9c6f0e",
  4: "#b34e00",
  5: "#c62828",
};

export const LIBELLE_NOTE: Record<number, string> = {
  1: "risque faible",
  2: "risque modéré",
  3: "à surveiller",
  4: "prioritaire",
  5: "critique",
};

export const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export const NB = new Intl.NumberFormat("fr-FR");

/** Décimales à la française : séparateur virgule, pas point. */
export const DEC = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

export const PCT = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
