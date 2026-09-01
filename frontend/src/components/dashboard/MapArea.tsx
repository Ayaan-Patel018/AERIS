import React, { useRef, useEffect, useState, useCallback } from 'react';
import L from 'leaflet';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { useLeafletMap, type TileLayerKey } from './LeafletMap';
import { drawVehicleMarker } from './VehicleMarker';
import type { TrajectoryPoint } from '../../hooks/useTrajectoryData';

// ── Caption shown when smoothed layer is on ───────────────────────────────────
const SMOOTHED_CAPTION =
  'Post-processed using the complete recorded drive — not available to a live system.';

// ── Metric utilities ──────────────────────────────────────────────────────────
/**
 * Returns how many metres correspond to one pixel at the given Leaflet zoom
 * level and latitude. Used to convert uncertainty radii (metres) to canvas pixels.
 */
function metersPerPixel(zoom: number, lat: number): number {
  const earthCircum = 40_075_016.686; // metres
  return (earthCircum * Math.cos((lat * Math.PI) / 180)) / (256 * Math.pow(2, zoom));
}

// ── Canvas draw helpers ───────────────────────────────────────────────────────
/**
 * Draw a trajectory path in Leaflet-projected pixel space.
 * Each point is converted via `map.latLngToContainerPoint()` so the path
 * stays perfectly aligned with map tiles at any zoom/pan.
 */
function drawLatLngPath(
  ctx: CanvasRenderingContext2D,
  points: TrajectoryPoint[],
  map: L.Map,
  color: string,
  lineWidth: number,
  dashed = false,
) {
  if (!points.length) return;
  ctx.save();
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.setLineDash(dashed ? [5, 4] : []);

  let started = false;
  for (const p of points) {
    const pt = map.latLngToContainerPoint([p.lat, p.lon]);
    if (!started) { ctx.moveTo(pt.x, pt.y); started = true; }
    else ctx.lineTo(pt.x, pt.y);
  }
  ctx.stroke();
  ctx.restore();
}

/**
 * Draw a filled circle representing positional uncertainty.
 * `radiusM` is in metres; converted to pixels using `metersPerPixel()`.
 */
function drawUncertaintyPx(
  ctx: CanvasRenderingContext2D,
  px: number,
  py: number,
  radiusM: number,
  map: L.Map,
  lat: number,
  color: string,
) {
  const mpp = metersPerPixel(map.getZoom(), lat);
  const rPx = Math.max(4, radiusM / mpp); // at least 4 px so it's always visible
  ctx.save();
  ctx.beginPath();
  ctx.arc(px, py, rPx, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.restore();
}

// ── Component ─────────────────────────────────────────────────────────────────
export const MapArea: React.FC = () => {
  const { layers } = useDashboardContext();
  const { gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos } =
    useTrajectoryData();
  const { isOutage, aerisError, gnssError } = useGNSSStatus();

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const wrapRef    = useRef<HTMLDivElement>(null);
  const leafletEl  = useRef<HTMLDivElement>(null);
  const canvasRef  = useRef<HTMLCanvasElement>(null);

  // ── Map state ─────────────────────────────────────────────────────────────
  const mapRef            = useRef<L.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // ── HUD state (local — does not need to be in context) ────────────────────
  const [activeTile, setActiveTile] = useState<TileLayerKey>('dark');
  const [autoFollow, setAutoFollow]  = useState(false);

  // Refs to avoid stale closures in Leaflet event handlers
  const autoFollowRef         = useRef(autoFollow);
  const isFollowPanningRef    = useRef(false); // prevents recursive move-event redraws
  const drawFnRef             = useRef<(() => void) | null>(null);

  useEffect(() => { autoFollowRef.current = autoFollow; }, [autoFollow]);

  // ── Initialise Leaflet (headless hook) ────────────────────────────────────
  useLeafletMap({
    containerEl: leafletEl.current,
    activeTile,
    center: [52.3705, -1.2544], // Rugby UK — route centre
    zoom: 15,
    onMapReady: useCallback((map: L.Map) => {
      mapRef.current = map;

      // Fit to full ground-truth route bounds on first load
      const bounds = L.latLngBounds(gt.map(p => [p.lat, p.lon] as [number, number]));
      map.fitBounds(bounds, { padding: [48, 48], animate: false });

      // Redraw canvas whenever the map moves or zooms
      map.on('move viewreset zoom', () => {
        if (!isFollowPanningRef.current) {
          drawFnRef.current?.();
        }
      });

      setMapReady(true);
    // gt is a stable module-level constant so this dep is safe
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []),
  });

  // ── Canvas resize sync ────────────────────────────────────────────────────
  useEffect(() => {
    const cv = canvasRef.current;
    const wrap = wrapRef.current;
    if (!cv || !wrap) return;

    const obs = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        cv.width  = width;
        cv.height = height;
        mapRef.current?.invalidateSize();
        drawFnRef.current?.();
      }
    });
    obs.observe(wrap);
    return () => obs.disconnect();
  }, []);

  // ── Main draw loop ────────────────────────────────────────────────────────
  // This useEffect runs on every React render (progress changes drive renders
  // at ~60 FPS via usePlayback's requestAnimationFrame loop).
  useEffect(() => {
    const cv  = canvasRef.current;
    const map = mapRef.current;
    if (!cv || !map || !mapReady) return;

    const ctx = cv.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const w = cv.offsetWidth;
      const h = cv.offsetHeight;
      if (cv.width !== w) cv.width = w;
      if (cv.height !== h) cv.height = h;
      ctx.clearRect(0, 0, cv.width, cv.height);

      // ── Auto-follow: pan map to keep vehicle centred ──────────────────────
      if (autoFollowRef.current && currentFusedPos) {
        isFollowPanningRef.current = true;
        map.panTo([currentFusedPos.lat, currentFusedPos.lon], { animate: false });
        isFollowPanningRef.current = false;
      }

      const slice = (arr: TrajectoryPoint[]) => arr.slice(0, currentIndex + 1);

      // ── Trajectory lines ──────────────────────────────────────────────────
      // Ground truth — subtle dark line (always below others)
      if (layers.gt && gt.length) {
        drawLatLngPath(ctx, slice(gt), map, '#3E3E4A', 1.5, true);
      }

      // GNSS only — cyan
      if (layers.gnss && gnss.length) {
        drawLatLngPath(ctx, slice(gnss), map, '#2DD4BF', 2, false);
      }

      // AERIS real-time fused — orange
      if (layers.fused && fused.length) {
        drawLatLngPath(ctx, slice(fused), map, '#F0801E', 2, false);
      }

      // Offline smoothed (RTS+ZARU) — violet/purple
      if (layers.smoothed && smoothed.length) {
        drawLatLngPath(ctx, slice(smoothed), map, '#A78BFA', 2, false);
      }

      // ── Uncertainty circles (metric-correct via metersPerPixel) ───────────
      if (layers.gnss && isOutage && currentGnssPos) {
        const pt = map.latLngToContainerPoint([currentGnssPos.lat, currentGnssPos.lon]);
        drawUncertaintyPx(ctx, pt.x, pt.y, gnssError * 2, map, currentGnssPos.lat, 'rgba(45,212,191,0.15)');
      }
      if (layers.fused && isOutage && currentFusedPos) {
        const pt = map.latLngToContainerPoint([currentFusedPos.lat, currentFusedPos.lon]);
        drawUncertaintyPx(ctx, pt.x, pt.y, aerisError * 2, map, currentFusedPos.lat, 'rgba(240,128,30,0.15)');
      }

      // ── Vehicle marker — follows fused layer only, no silent fallback ──────
      if (layers.fused && currentFusedPos) {
        const pt = map.latLngToContainerPoint([currentFusedPos.lat, currentFusedPos.lon]);
        let heading = 0;
        if (currentIndex > 0 && fused[currentIndex - 1]) {
          const prev = map.latLngToContainerPoint([
            fused[currentIndex - 1].lat,
            fused[currentIndex - 1].lon,
          ]);
          heading = Math.atan2(pt.y - prev.y, pt.x - prev.x);
        }
        // Marker drawn in screen-space (no ctx transform needed)
        drawVehicleMarker(ctx, pt.x, pt.y, heading, isOutage ? '#F0801E' : '#2DD4BF');
      }

      // ── Smoothed caption overlay (screen-space, always legible) ───────────
      if (layers.smoothed) {
        const pad  = 12;
        const capH = 26;
        const capY = h - capH - pad;
        ctx.save();
        ctx.font = '10px "IBM Plex Mono", monospace';
        const textW = ctx.measureText(SMOOTHED_CAPTION).width;
        ctx.fillStyle = 'rgba(10,10,11,0.82)';
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(pad - 8, capY - 2, textW + 16, capH, 4);
        else ctx.rect(pad - 8, capY - 2, textW + 16, capH);
        ctx.fill();
        ctx.fillStyle = '#A78BFA';
        ctx.fillRect(pad - 8, capY - 2, 3, capH);
        ctx.fillStyle = 'rgba(244,241,234,0.75)';
        ctx.fillText(SMOOTHED_CAPTION, pad + 2, capY + capH / 2 + 4);
        ctx.restore();
      }
    };

    drawFnRef.current = draw;
    draw();
  }); // no deps — runs every render

  // ── HUD actions ───────────────────────────────────────────────────────────
  const fitRoute = useCallback(() => {
    if (!mapRef.current || !gt.length) return;
    const bounds = L.latLngBounds(gt.map(p => [p.lat, p.lon] as [number, number]));
    mapRef.current.fitBounds(bounds, { padding: [48, 48] });
  }, []);

  const zoomIn  = useCallback(() => mapRef.current?.zoomIn(),  []);
  const zoomOut = useCallback(() => mapRef.current?.zoomOut(), []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div ref={wrapRef} className="portal-canvas-wrap">

      {/* Layer 1: Leaflet tile map */}
      <div
        ref={leafletEl}
        style={{ position: 'absolute', inset: 0, zIndex: 0 }}
      />

      {/* Layer 2: Trajectory canvas overlay — pointer-events:none so Leaflet
          handles mouse interaction (pan/zoom/touch) natively */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 10,
          pointerEvents: 'none',
          display: 'block',
        }}
      />

      {/* Layer 3: HUD controls */}
      <div className="map-hud" style={{ zIndex: 20 }}>

        {/* Tile layer switcher */}
        <div className="hud-tiles">
          {(['dark', 'osm', 'sat'] as TileLayerKey[]).map(key => (
            <button
              key={key}
              className={`hud-tile-btn ${activeTile === key ? 'active' : ''}`}
              onClick={() => setActiveTile(key)}
              title={key === 'dark' ? 'CartoDB Dark Matter' : key === 'osm' ? 'OpenStreetMap Streets' : 'Esri World Imagery Satellite'}
            >
              {key === 'dark' ? 'DARK' : key === 'osm' ? 'OSM' : 'SAT'}
            </button>
          ))}
        </div>

        {/* Fit route */}
        <button className="hud-btn" onClick={fitRoute} title="Fit route to view" id="hudFitRoute">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="1" y="1" width="4" height="4" rx="0.5"/>
            <rect x="9" y="1" width="4" height="4" rx="0.5"/>
            <rect x="1" y="9" width="4" height="4" rx="0.5"/>
            <rect x="9" y="9" width="4" height="4" rx="0.5"/>
          </svg>
        </button>

        {/* Auto-follow toggle */}
        <button
          className={`hud-btn ${autoFollow ? 'active' : ''}`}
          onClick={() => setAutoFollow(v => !v)}
          title={autoFollow ? 'Following vehicle (click to stop)' : 'Auto-follow vehicle'}
          id="hudAutoFollow"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="7" cy="7" r="5"/>
            <circle cx="7" cy="7" r="1.5" fill="currentColor" stroke="none"/>
            <line x1="7" y1="1" x2="7" y2="3"/>
            <line x1="7" y1="11" x2="7" y2="13"/>
            <line x1="1" y1="7" x2="3" y2="7"/>
            <line x1="11" y1="7" x2="13" y2="7"/>
          </svg>
        </button>

        {/* Zoom */}
        <button className="hud-btn" onClick={zoomIn}  title="Zoom in"  id="hudZoomIn">+</button>
        <button className="hud-btn" onClick={zoomOut} title="Zoom out" id="hudZoomOut">−</button>
      </div>

    </div>
  );
};
