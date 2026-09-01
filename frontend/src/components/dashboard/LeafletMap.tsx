import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export type TileLayerKey = 'dark' | 'osm' | 'sat';

interface LeafletMapProps {
  /** Called once the Leaflet map instance is ready */
  onMapReady: (map: L.Map) => void;
  /** Currently active tile layer key */
  activeTile: TileLayerKey;
  /** Initial map centre [lat, lon] */
  center: [number, number];
  /** Initial zoom level */
  zoom: number;
  /** The DOM element to mount Leaflet into */
  containerEl: HTMLElement | null;
}

export const TILE_CONFIGS: Record<TileLayerKey, {
  url: string;
  attribution: string;
  maxZoom: number;
}> = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
      '&copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 20,
  },
  osm: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  sat: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution:
      'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, ' +
      'Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 18,
  },
};

/**
 * Headless hook that mounts a Leaflet map into the given DOM element.
 * Exposes the map instance via `onMapReady` and handles tile layer swapping.
 * No JSX — the caller owns the container div.
 */
export function useLeafletMap({
  onMapReady,
  activeTile,
  center,
  zoom,
  containerEl,
}: LeafletMapProps) {
  const mapRef      = useRef<L.Map | null>(null);
  const tileRef     = useRef<L.TileLayer | null>(null);
  const initialised = useRef(false);

  // ── Mount / unmount ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerEl || initialised.current) return;
    initialised.current = true;

    const cfg = TILE_CONFIGS[activeTile];
    const map = L.map(containerEl, {
      center,
      zoom,
      zoomControl:       false, // we provide our own HUD zoom buttons
      attributionControl: true,
      preferCanvas:      true,  // faster rendering for our use case
    });

    tileRef.current = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom:     cfg.maxZoom,
    }).addTo(map);

    mapRef.current = map;
    onMapReady(map);

    return () => {
      initialised.current = false;
      map.remove();
      mapRef.current  = null;
      tileRef.current = null;
    };
  // containerEl reference only matters on first non-null value;
  // other deps intentionally omitted to prevent map re-creation.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerEl]);

  // ── Swap tile layer when activeTile changes ──────────────────────────────
  useEffect(() => {
    if (!mapRef.current || !tileRef.current) return;
    const map = mapRef.current;

    map.removeLayer(tileRef.current);
    const cfg = TILE_CONFIGS[activeTile];
    tileRef.current = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom:     cfg.maxZoom,
    }).addTo(map);
  }, [activeTile]);

  return mapRef;
}
