/**
 * Carte du risque : réseau simulé posé sur le fond de carte réel de la ville.
 *
 * Le tracé est FICTIF ; seul le fond de carte est réel. Il sert à donner une
 * échelle et une lisibilité urbaine que des coordonnées abstraites ne donnent
 * pas (« ce feeder critique traverse le centre » se lit, « x = 420 m » non).
 *
 * Accessibilité : la carte est un complément visuel déclaré `role="img"`, et
 * tout ce qu'elle permet (sélectionner un tronçon, lire ses caractéristiques)
 * reste faisable au clavier depuis l'onglet Tableau. La couleur n'est jamais
 * seule porteuse d'information : la note est écrite dans l'infobulle, dans la
 * légende et dans la fiche.
 */
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";

import { Bbox, Ville } from "./api";
import { COULEUR_NOTE, NOTES, PCT } from "./notes";

const VIDE: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

// Le fond OpenStreetMap est en tuiles raster : pas de clé d'API, attribution
// obligatoire (affichée par le contrôle d'attribution de MapLibre).
const STYLE_OSM: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const COULEUR_PAR_NOTE = [
  "match",
  ["get", "note"],
  ...NOTES.flatMap((n) => [n, COULEUR_NOTE[n]]),
  "#607d8b",
];

// Les notes fortes sont plus épaisses : l'information passe par l'épaisseur
// autant que par la teinte, pour rester lisible en vision des couleurs déficiente.
const EPAISSEUR = ["interpolate", ["linear"], ["get", "note"], 1, 1.6, 5, 4.4];

function rectangle(
  ouest: number, sud: number, est: number, nord: number,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [
            [[ouest, sud], [est, sud], [est, nord], [ouest, nord], [ouest, sud]],
          ],
        },
      },
    ],
  };
}

interface Props {
  ville: Ville | null;
  geo: GeoJSON.FeatureCollection | null;
  selection: string | null;
  onSelection: (id: string) => void;
  /** Incrémenté quand la sélection vient du tableau : la carte doit alors s'y
      rendre, puisque l'utilisateur ne sait pas où le tronçon se trouve. Un clic
      sur la carte ne l'incrémente pas, sinon la vue sauterait sous le curseur. */
  recentrage: number;
  /** L'onglet Carte est-il affiché ? Masqué, son canevas mesure zéro et tout
      cadrage calculé pendant ce temps tombe à côté. */
  visible: boolean;
  modeDessin: boolean;
  emprise: Bbox | null;
  onEmprise: (b: Bbox | null) => void;
}

export function Carte({
  ville, geo, selection, onSelection, recentrage, visible, modeDessin, emprise, onEmprise,
}: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<maplibregl.Map | null>(null);
  const [prete, setPrete] = useState(false);
  // Les rappels changent à chaque rendu ; les garder dans une ref évite de
  // réabonner les écouteurs MapLibre (et de perdre le tracé en cours).
  const surSelection = useRef(onSelection);
  const surEmprise = useRef(onEmprise);
  surSelection.current = onSelection;
  surEmprise.current = onEmprise;

  useEffect(() => {
    if (!conteneur.current || carte.current) return;
    const map = new maplibregl.Map({
      container: conteneur.current,
      style: STYLE_OSM,
      center: [2.3522, 48.8566],
      zoom: 12,
    });
    carte.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }));

    const infobulle = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "infobulle",
    });

    map.on("load", () => {
      map.addSource("troncons", { type: "geojson", data: VIDE });
      map.addSource("emprise", { type: "geojson", data: VIDE });

      // Liseré blanc sous le tracé : détache n'importe quelle teinte du fond
      // de carte sans avoir à changer la palette des notes.
      map.addLayer({
        id: "troncons-lisere",
        type: "line",
        source: "troncons",
        paint: {
          "line-color": "#ffffff",
          "line-width": ["+", EPAISSEUR, 2.4] as never,
          "line-opacity": 0.85,
        },
      });
      map.addLayer({
        id: "troncons",
        type: "line",
        source: "troncons",
        paint: { "line-color": COULEUR_PAR_NOTE as never, "line-width": EPAISSEUR as never },
      });
      map.addLayer({
        id: "troncons-selection",
        type: "line",
        source: "troncons",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#00363a", "line-width": ["+", EPAISSEUR, 5] as never },
      });
      map.addLayer({
        id: "emprise",
        type: "fill",
        source: "emprise",
        paint: { "fill-color": "#00676c", "fill-opacity": 0.08 },
      });
      map.addLayer({
        id: "emprise-bord",
        type: "line",
        source: "emprise",
        paint: { "line-color": "#00676c", "line-width": 2 },
      });
      setPrete(true);
    });

    map.on("mousemove", "troncons", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      map.getCanvas().style.cursor = "pointer";
      const p = f.properties as Record<string, string | number>;
      const proba = Number(p.score_h3);
      infobulle
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${p.id}</strong> note ${p.note}<br>` +
            `<span>${p.materiau}, Ø${p.diametre_mm} mm, posé en ${p.annee_pose}` +
            `${Number.isFinite(proba) ? `, P(casse) 3 ans ${PCT.format(proba)}` : ""}` +
            `</span>`,
        )
        .addTo(map);
    });
    map.on("mouseleave", "troncons", () => {
      map.getCanvas().style.cursor = "";
      infobulle.remove();
    });
    map.on("click", "troncons", (e) => {
      const id = e.features?.[0]?.properties?.id;
      if (typeof id === "string") surSelection.current(id);
    });

    return () => {
      infobulle.remove();
      map.remove();
      carte.current = null;
      setPrete(false);
    };
  }, []);

  /* Recentrage sur la ville choisie. */
  useEffect(() => {
    if (!carte.current || !ville) return;
    carte.current.jumpTo({ center: [ville.centre_lon, ville.centre_lat], zoom: ville.zoom });
  }, [ville]);

  /* Données du réseau. */
  useEffect(() => {
    if (!carte.current || !prete) return;
    const src = carte.current.getSource("troncons") as maplibregl.GeoJSONSource | undefined;
    src?.setData(geo ?? VIDE);
  }, [geo, prete]);

  /* Mise en évidence du tronçon sélectionné. */
  useEffect(() => {
    if (!carte.current || !prete) return;
    carte.current.setFilter("troncons-selection", ["==", ["get", "id"], selection ?? ""]);
  }, [selection, prete]);

  /* Reprise des dimensions au retour sur l'onglet. Déclaré AVANT le recentrage
     pour que celui-ci calcule son cadrage sur un canevas déjà remesuré. */
  useEffect(() => {
    if (!carte.current || !prete || !visible) return;
    carte.current.resize();
  }, [visible, prete]);

  /* Aller au tronçon choisi depuis le tableau. */
  useEffect(() => {
    const map = carte.current;
    if (!map || !prete || !recentrage || !selection) return;
    const trouve = geo?.features.find((f) => f.properties?.id === selection);
    if (!trouve) return;
    const points = (trouve.geometry as GeoJSON.LineString).coordinates as [number, number][];
    const cadre = points.reduce(
      (b, p) => b.extend(p),
      new maplibregl.LngLatBounds(points[0], points[0]),
    );
    const sobre = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Marge proportionnelle au canevas : une valeur fixe dépasse la hauteur
    // disponible sur écran court et MapLibre refuse alors le cadrage.
    const canevas = map.getCanvas();
    const marge = Math.floor(Math.min(canevas.clientWidth, canevas.clientHeight) / 5);
    map.fitBounds(cadre, { padding: marge, maxZoom: 15, animate: !sobre, duration: 600 });
    // `geo` est volontairement hors dépendances : seule une nouvelle demande de
    // recentrage doit déplacer la vue, pas un rechargement des données.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentrage, prete]);

  /* L'emprise affichée suit l'état : le tracé en cours est local, le rectangle
     définitif redescend depuis App une fois le glisser terminé. */
  useEffect(() => {
    if (!carte.current || !prete) return;
    const src = carte.current.getSource("emprise") as maplibregl.GeoJSONSource | undefined;
    src?.setData(emprise ? rectangle(...emprise) : VIDE);
  }, [emprise, prete]);

  /* Dessin de l'emprise : glisser-déposer d'un rectangle. */
  useEffect(() => {
    const map = carte.current;
    if (!map || !prete || !modeDessin) return;

    map.dragPan.disable();
    map.getCanvas().style.cursor = "crosshair";
    let depart: maplibregl.LngLat | null = null;
    const source = () => map.getSource("emprise") as maplibregl.GeoJSONSource | undefined;

    const debut = (e: maplibregl.MapMouseEvent) => {
      depart = e.lngLat;
    };
    const trace = (e: maplibregl.MapMouseEvent) => {
      if (!depart) return;
      source()?.setData(
        rectangle(
          Math.min(depart.lng, e.lngLat.lng), Math.min(depart.lat, e.lngLat.lat),
          Math.max(depart.lng, e.lngLat.lng), Math.max(depart.lat, e.lngLat.lat),
        ),
      );
    };
    const fin = (e: maplibregl.MapMouseEvent) => {
      if (!depart) return;
      const a = depart;
      depart = null;
      // Un simple clic n'est pas une emprise : sous un seuil visible, on annule.
      if (Math.abs(a.lat - e.lngLat.lat) < 0.0008 || Math.abs(a.lng - e.lngLat.lng) < 0.0008) {
        surEmprise.current(null);
        return;
      }
      surEmprise.current([
        Math.min(a.lng, e.lngLat.lng), Math.min(a.lat, e.lngLat.lat),
        Math.max(a.lng, e.lngLat.lng), Math.max(a.lat, e.lngLat.lat),
      ]);
    };

    map.on("mousedown", debut);
    map.on("mousemove", trace);
    map.on("mouseup", fin);
    return () => {
      map.off("mousedown", debut);
      map.off("mousemove", trace);
      map.off("mouseup", fin);
      map.dragPan.enable();
      map.getCanvas().style.cursor = "";
    };
  }, [modeDessin, prete]);

  return (
    <div
      ref={conteneur}
      className="carte"
      role="img"
      aria-label={
        ville
          ? `Réseau simulé sur le fond de carte de ${ville.nom}, tracés colorés du vert ` +
            "(note 1, risque faible) au rouge (note 5, critique). Les mêmes tronçons sont " +
            "consultables au clavier dans l'onglet Tableau."
          : "Chargement de la carte"
      }
    />
  );
}
