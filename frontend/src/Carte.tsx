/**
 * Carte MapLibre des tronçons, colorés par Note 1–5.
 *
 * Les coordonnées synthétiques sont locales (mètres autour de l'origine) :
 * on les projette en pseudo-degrés (÷ 111 320) pour MapLibre — suffisant pour
 * une démo sans fond de carte réel (fond neutre, pas de tuiles externes).
 */
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import { api } from "./api";

const M_PAR_DEGRE = 111_320;
const COULEURS: [number, string][] = [
  [1, "#2e7d32"],
  [2, "#9e9d24"],
  [3, "#f9a825"],
  [4, "#ef6c00"],
  [5, "#c62828"],
];

export function Carte({ noteMin }: { noteMin: number }) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!conteneur.current || carte.current) return;
    carte.current = new maplibregl.Map({
      container: conteneur.current,
      style: { version: 8, sources: {}, layers: [{ id: "fond", type: "background", paint: { "background-color": "#f4f2ee" } }] },
      center: [0, 0],
      zoom: 12,
      attributionControl: false,
    });
    carte.current.addControl(new maplibregl.NavigationControl(), "top-right");
  }, []);

  useEffect(() => {
    const map = carte.current;
    if (!map) return;
    const charger = async () => {
      const geo = await api.geojson(noteMin);
      for (const f of geo.features) {
        const g = f.geometry as GeoJSON.LineString;
        g.coordinates = g.coordinates.map(([x, y]) => [x / M_PAR_DEGRE, y / M_PAR_DEGRE]);
      }
      const src = map.getSource("troncons") as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(geo);
      } else {
        map.addSource("troncons", { type: "geojson", data: geo });
        map.addLayer({
          id: "troncons",
          type: "line",
          source: "troncons",
          paint: {
            "line-width": ["interpolate", ["linear"], ["get", "note"], 1, 1.2, 5, 3.5],
            "line-color": ["match", ["get", "note"], ...COULEURS.flat(), "#607d8b"] as never,
          },
        });
      }
    };
    if (map.isStyleLoaded()) void charger();
    else map.once("load", () => void charger());
  }, [noteMin]);

  return (
    <div
      ref={conteneur}
      className="carte"
      role="img"
      aria-label={`Carte du réseau synthétique, tronçons de note ${noteMin} et plus, colorés du vert (note 1) au rouge (note 5)`}
    />
  );
}
