import React, { useRef, useEffect, useState, useCallback } from "react";
import L from "leaflet";
import { useDashboardContext } from "../../context/DashboardContext";
import { useTrajectoryData, type TrajectoryPoint } from "../../hooks/useTrajectoryData";
import { useGNSSStatus } from "../../hooks/useGNSSStatus";
import { drawVehicleMarker } from "./VehicleMarker";
import { drawUncertaintyCircle, drawCovarianceEllipse } from "./UncertaintyCircle";

type TileStyle = "dark" | "streets" | "satellite";

const TILE_LAYERS: Record<TileStyle, { url: string; attribution: string; maxZoom: number; subdomains?: string[] }> = {
  dark: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
    subdomains: ["a", "b", "c"],
  },
  streets: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
    subdomains: ["a", "b", "c"],
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri",
    maxZoom: 19,
  },
};

// ── Trajectory drawing (inline — supports per-segment dashing) ──────────────
function drawSegmentedTrajectory(
  ctx: CanvasRenderingContext2D,
  pts: { x: number; y: number; outage: boolean }[],
  solidColor: string,
  outageColor: string,
  solidWidth: number,
  outageWidth: number
) {
  if (pts.length < 2) return;

  // Walk the array and emit a new sub-path each time outage state toggles
  let i = 0;
  while (i < pts.length - 1) {
    const isOut = pts[i].outage;
    const startI = i;

    // Advance while state matches
    while (i < pts.length - 1 && pts[i + 1].outage === isOut) i++;

    // Draw this run
    ctx.beginPath();
    ctx.strokeStyle = isOut ? outageColor : solidColor;
    ctx.lineWidth   = isOut ? outageWidth : solidWidth;
    if (isOut) {
      ctx.setLineDash([6, 5]);
    } else {
      ctx.setLineDash([]);
    }
    ctx.moveTo(pts[startI].x, pts[startI].y);
    for (let j = startI + 1; j <= i; j++) {
      ctx.lineTo(pts[j].x, pts[j].y);
    }
    ctx.stroke();
    i++;
  }
  ctx.setLineDash([]);
}

function drawSolidTrajectory(
  ctx: CanvasRenderingContext2D,
  pts: { x: number; y: number }[],
  color: string,
  width: number,
  dashed = false
) {
  if (pts.length < 2) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.setLineDash(dashed ? [5, 5] : []);
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.stroke();
  ctx.setLineDash([]);
}

// ── Tooltip data type ───────────────────────────────────────────────────────
interface HoverTooltip {
  x: number;          // canvas px
  y: number;
  timestamp: string;  // formatted real time
  speed: string;
  heading: string;
  uncertainty: string;
}

export const MapArea: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef          = useRef<L.Map | null>(null);
  const tileLayerRef    = useRef<L.TileLayer | null>(null);
  const canvasRef       = useRef<HTMLCanvasElement>(null);
  const animFrameRef    = useRef<number | null>(null);

  const lastFusedHeadingRef    = useRef<number>(0);
  const lastGnssHeadingRef     = useRef<number>(0);
  const lastSmoothedHeadingRef = useRef<number>(0);

  // autoFollow: true = camera tracks vehicle; false = user panned freely
  const [autoFollow, setAutoFollow] = useState<boolean>(true);
  // userPanned: becomes true the moment user drags the map; triggers "RECENTER" pill
  const [userPanned, setUserPanned] = useState<boolean>(false);
  const [tileStyle, setTileStyle]   = useState<TileStyle>("dark");
  const [tooltip, setTooltip]       = useState<HoverTooltip | null>(null);

  const { layers, totalDurationS } = useDashboardContext();
  const { gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos } = useTrajectoryData();
  const { isOutage, aerisError, gnssError } = useGNSSStatus();

  // Trajectory geographical bounding box
  const getTrajectoryBounds = useCallback((): L.LatLngBounds | null => {
    const pts = gt.length ? gt : fused;
    const valid = pts.filter((p) => p.lat !== undefined && p.lon !== undefined);
    if (!valid.length) return null;
    const lats = valid.map((p) => p.lat!);
    const lons = valid.map((p) => p.lon!);
    return L.latLngBounds([Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]);
  }, [gt, fused]);

  // ── Initialize Leaflet Map ──────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [fused[0]?.lat ?? 52.37045, fused[0]?.lon ?? -1.25444],
      zoom: 16,
      zoomControl: false,
      attributionControl: false,
    });

    const cfg = TILE_LAYERS[tileStyle];
    tileLayerRef.current = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: cfg.maxZoom,
      subdomains: cfg.subdomains ?? ["a", "b", "c"],
    }).addTo(map);

    mapRef.current = map;

    // §3.8 — detect user manual pan to show RECENTER button
    const onDragStart = () => {
      setUserPanned(true);
      setAutoFollow(false);
    };
    map.on("dragstart", onDragStart);

    return () => {
      map.off("dragstart", onDragStart);
      map.remove();
      mapRef.current = null;
    };
  }, [fused]);          // intentionally omit tileStyle — handled separately below

  // Tile style switching
  useEffect(() => {
    if (!mapRef.current) return;
    if (tileLayerRef.current) mapRef.current.removeLayer(tileLayerRef.current);
    const cfg = TILE_LAYERS[tileStyle];
    tileLayerRef.current = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: cfg.maxZoom,
      subdomains: cfg.subdomains ?? ["a", "b", "c"],
    }).addTo(mapRef.current);
  }, [tileStyle]);

  // ── Canvas render ───────────────────────────────────────────────────────────
  const renderCanvas = useCallback(() => {
    const map = mapRef.current;
    const cv  = canvasRef.current;
    if (!map || !cv) return;

    const ctx = cv.getContext("2d");
    if (!ctx) return;

    const size = map.getSize();
    if (cv.width !== size.x || cv.height !== size.y) {
      cv.width  = size.x;
      cv.height = size.y;
    }
    ctx.clearRect(0, 0, cv.width, cv.height);

    const toPixel = (lat: number, lon: number) => {
      const pt = map.latLngToContainerPoint([lat, lon]);
      return { x: pt.x, y: pt.y };
    };

    const getPixelRadius = (lat: number, lon: number, radiusM: number): number => {
      if (radiusM <= 0) return 0;
      const centre = map.latLngToContainerPoint([lat, lon]);
      const edge   = map.latLngToContainerPoint([lat + radiusM / 111320, lon]);
      return Math.max(4, Math.abs(centre.y - edge.y));
    };

    const getHeadingRad = (
      pos: TrajectoryPoint | undefined,
      prev: TrajectoryPoint | undefined,
      ref: { current: number }
    ): number => {
      if (pos?.heading !== undefined && !isNaN(pos.heading)) {
        const rad = ((pos.heading - 90) * Math.PI) / 180;
        ref.current = rad;
        return rad;
      }
      if (pos?.lat && pos?.lon && prev?.lat && prev?.lon) {
        const p1 = toPixel(prev.lat, prev.lon);
        const p2 = toPixel(pos.lat, pos.lon);
        const dx = p2.x - p1.x, dy = p2.y - p1.y;
        if (Math.hypot(dx, dy) > 0.4) {
          const rad = Math.atan2(dy, dx);
          ref.current = rad;
          return rad;
        }
      }
      return ref.current;
    };

    // ── 1. Ground-truth reference (grey dashed) — labeled "Reference (VBOX)" ─
    if (layers.gt && gt.length > 1) {
      const px: { x: number; y: number }[] = [];
      for (const p of gt) {
        if (p.lat !== undefined && p.lon !== undefined) px.push(toPixel(p.lat, p.lon));
      }
      drawSolidTrajectory(ctx, px, "#4A4A54", 1.5, true);
    }

    // ── 2. Raw GNSS traveled path (cyan) ─────────────────────────────────────
    if (layers.gnss && gnss.length > 1) {
      const px: { x: number; y: number }[] = [];
      const end = Math.min(currentIndex, gnss.length - 1);
      for (let i = 0; i <= end; i++) {
        if (gnss[i].lat !== undefined && gnss[i].lon !== undefined)
          px.push(toPixel(gnss[i].lat!, gnss[i].lon!));
      }
      if (px.length > 1) drawSolidTrajectory(ctx, px, "#2DD4BF", 2.2);
    }

    // ── 3. AERIS ES-EKF traveled path — §3.6 outage segments rendered dashed ──
    if (layers.fused && fused.length > 1) {
      const end = Math.min(currentIndex, fused.length - 1);
      const pts: { x: number; y: number; outage: boolean }[] = [];
      for (let i = 0; i <= end; i++) {
        const p = fused[i];
        if (p.lat !== undefined && p.lon !== undefined) {
          pts.push({
            ...toPixel(p.lat, p.lon),
            outage: p.status === "outage" || p.status === "unavailable",
          });
        }
      }
      if (pts.length > 1) {
        drawSegmentedTrajectory(
          ctx,
          pts,
          "#F0801E",           // AERIS orange — GNSS-aided segments
          "#C0601080",         // dimmer orange — dead-reckoning (outage) segments
          2.6,
          2.2
        );
      }
    }

    // ── 4. RTS Smoothed traveled path (purple) ────────────────────────────────
    if (layers.smoothed && smoothed && smoothed.length > 1) {
      const px: { x: number; y: number }[] = [];
      const end = Math.min(currentIndex, smoothed.length - 1);
      for (let i = 0; i <= end; i++) {
        if (smoothed[i].lat !== undefined && smoothed[i].lon !== undefined)
          px.push(toPixel(smoothed[i].lat!, smoothed[i].lon!));
      }
      if (px.length > 1) drawSolidTrajectory(ctx, px, "#A855F7", 2.8);
    }

    const activeCount = (layers.gnss ? 1 : 0) + (layers.fused ? 1 : 0) + (layers.smoothed ? 1 : 0);

    // ── 5A. GNSS vehicle marker ───────────────────────────────────────────────
    if (layers.gnss && currentGnssPos && currentGnssPos.status !== "unavailable" &&
        currentGnssPos.lat !== undefined && currentGnssPos.lon !== undefined) {
      const pt    = toPixel(currentGnssPos.lat, currentGnssPos.lon);
      const prev  = currentIndex > 0 ? gnss[currentIndex - 1] : undefined;
      const h     = getHeadingRad(currentGnssPos, prev, lastGnssHeadingRef);
      const color = isOutage ? "#E5484D" : "#2DD4BF";
      if (isOutage) {
        drawUncertaintyCircle(ctx, pt.x, pt.y, getPixelRadius(currentGnssPos.lat, currentGnssPos.lon, gnssError), "rgba(229,72,77,0.12)");
      }
      drawVehicleMarker(ctx, pt.x, pt.y, h, color, activeCount > 1 ? "GNSS" : undefined, isOutage, !layers.fused && !layers.smoothed, { dx: -44, dy: -20 });
    }

    // ── 5B. RTS Smoothed vehicle marker ──────────────────────────────────────
    if (layers.smoothed && currentSmoothedPos && currentSmoothedPos.lat !== undefined && currentSmoothedPos.lon !== undefined) {
      const pt   = toPixel(currentSmoothedPos.lat, currentSmoothedPos.lon);
      const prev = currentIndex > 0 ? smoothed[currentIndex - 1] : undefined;
      const h    = getHeadingRad(currentSmoothedPos, prev, lastSmoothedHeadingRef);
      drawVehicleMarker(ctx, pt.x, pt.y, h, "#A855F7", activeCount > 1 ? "RTS" : undefined, false, !layers.fused, { dx: 18, dy: 10 });
    }

    // ── 5C. AERIS ES-EKF vehicle marker + covariance ellipse ─────────────────
    if (layers.fused && currentFusedPos && currentFusedPos.lat !== undefined && currentFusedPos.lon !== undefined) {
      const pt       = toPixel(currentFusedPos.lat, currentFusedPos.lon);
      const prev     = currentIndex > 0 ? fused[currentIndex - 1] : undefined;
      const h        = getHeadingRad(currentFusedPos, prev, lastFusedHeadingRef);
      const hasCov   = currentFusedPos.cov_xx !== undefined && currentFusedPos.cov_yy !== undefined;
      const covColor = isOutage ? "rgba(240,128,30,0.28)" : "rgba(240,128,30,0.12)";
      const m2px     = (m: number) => getPixelRadius(currentFusedPos.lat!, currentFusedPos.lon!, m);

      if (hasCov) {
        drawCovarianceEllipse(ctx, pt.x, pt.y, currentFusedPos.cov_xx!, currentFusedPos.cov_yy!, currentFusedPos.cov_xy ?? 0, m2px, covColor, 2.0);
      } else if (isOutage || aerisError > 0.5) {
        drawUncertaintyCircle(ctx, pt.x, pt.y, getPixelRadius(currentFusedPos.lat, currentFusedPos.lon, aerisError), covColor);
      }
      drawVehicleMarker(ctx, pt.x, pt.y, h, "#F0801E", activeCount > 1 ? "ES-EKF" : undefined, isOutage, true, { dx: 18, dy: -20 });
    }
  }, [gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos, layers, isOutage, aerisError, gnssError]);

  // Continuous animation loop
  useEffect(() => {
    const loop = () => {
      renderCanvas();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
  }, [renderCanvas]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.on("move", renderCanvas);
    map.on("zoom", renderCanvas);
    map.on("viewreset", renderCanvas);
    return () => {
      map.off("move", renderCanvas);
      map.off("zoom", renderCanvas);
      map.off("viewreset", renderCanvas);
    };
  }, [renderCanvas]);

  // Auto-follow (only when autoFollow is true, i.e. user hasn't panned)
  useEffect(() => {
    const map = mapRef.current;
    if (map && autoFollow) {
      let pos: TrajectoryPoint | null = null;
      if (layers.fused) pos = currentFusedPos;
      else if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.gnss) pos = currentGnssPos;
      if (pos && pos.lat !== undefined && pos.lon !== undefined) {
        map.panInside([pos.lat, pos.lon], { padding: [100, 100], animate: false });
      }
    }
    renderCanvas();
  }, [currentIndex, autoFollow, currentFusedPos, currentGnssPos, currentSmoothedPos, layers, renderCanvas]);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;
    const obs = new ResizeObserver(() => {
      if (mapRef.current) { mapRef.current.invalidateSize(); renderCanvas(); }
    });
    obs.observe(container);
    return () => obs.disconnect();
  }, [renderCanvas]);

  // ── §3.7 Hover/click tooltip — find nearest fused point ────────────────────
  const handleCanvasMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const map = mapRef.current;
    if (!map || !layers.fused || !fused.length) { setTooltip(null); return; }

    const rect = canvasRef.current!.getBoundingClientRect();
    const mx   = e.clientX - rect.left;
    const my   = e.clientY - rect.top;

    // Search the traveled portion only
    const end   = Math.min(currentIndex, fused.length - 1);
    let bestI   = -1;
    let bestD   = Infinity;
    for (let i = 0; i <= end; i++) {
      const p = fused[i];
      if (p.lat === undefined || p.lon === undefined) continue;
      const { x, y } = map.latLngToContainerPoint([p.lat, p.lon]);
      const d = (x - mx) ** 2 + (y - my) ** 2;
      if (d < bestD) { bestD = d; bestI = i; }
    }

    if (bestI < 0 || bestD > 400) { setTooltip(null); return; } // >20px away

    const p    = fused[bestI];
    const pt   = map.latLngToContainerPoint([p.lat!, p.lon!]);
    const realSec   = p.t * totalDurationS;
    const m   = Math.floor(realSec / 60);
    const s   = Math.floor(realSec % 60);
    const unc = p.uncertainty !== undefined ? `±${Math.sqrt(Math.max(0, p.uncertainty)).toFixed(3)} m` : "--";
    const spd = p.velocity   !== undefined ? `${(p.velocity * 3.6).toFixed(1)} km/h` : "--";
    const hdg = p.heading    !== undefined ? `${(((p.heading % 360) + 360) % 360).toFixed(1)}°` : "--";

    setTooltip({
      x:    pt.x,
      y:    pt.y,
      timestamp: `${m}:${String(s).padStart(2, "0")}`,
      speed:     spd,
      heading:   hdg,
      uncertainty: unc,
    });
  }, [fused, currentIndex, layers.fused, totalDurationS]);

  const handleCanvasMouseLeave = useCallback(() => setTooltip(null), []);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handleFitRoute = () => {
    setAutoFollow(false);
    setUserPanned(false);
    const bounds = getTrajectoryBounds();
    if (mapRef.current && bounds) mapRef.current.fitBounds(bounds, { padding: [40, 40], animate: true });
  };

  const handleRecenter = () => {
    setAutoFollow(true);
    setUserPanned(false);
    const map = mapRef.current;
    if (map) {
      let pos: TrajectoryPoint | null = null;
      if (layers.fused) pos = currentFusedPos;
      else if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.gnss) pos = currentGnssPos;
      if (pos?.lat !== undefined && pos?.lon !== undefined) {
        map.setView([pos.lat, pos.lon], 16, { animate: true });
      }
    }
  };

  const handleToggleAutoFollow = () => {
    const next = !autoFollow;
    setAutoFollow(next);
    if (next) {
      setUserPanned(false);
      const map = mapRef.current;
      if (map) {
        let pos: TrajectoryPoint | null = null;
        if (layers.fused) pos = currentFusedPos;
        else if (layers.smoothed) pos = currentSmoothedPos;
        else if (layers.gnss) pos = currentGnssPos;
        if (pos?.lat !== undefined && pos?.lon !== undefined) {
          map.setView([pos.lat, pos.lon], 16, { animate: true });
        }
      }
    }
  };

  const handleZoomIn  = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();

  return (
    <div className="map-viewport-container">
      {/* Base Leaflet map */}
      <div id="leafletMap" ref={mapContainerRef} className={`portal-leaflet-map tile-${tileStyle}`} />

      {/* Canvas overlay — §3.7 hover events wired here */}
      <canvas
        id="mainCanvas"
        ref={canvasRef}
        style={{ width: "100%", height: "100%", display: "block", pointerEvents: "auto" }}
        onMouseMove={handleCanvasMouseMove}
        onMouseLeave={handleCanvasMouseLeave}
      />

      {/* §3.7 Hover tooltip */}
      {tooltip && (
        <div
          className="map-traj-tooltip"
          style={{ left: tooltip.x + 12, top: tooltip.y - 52 }}
          aria-hidden="true"
        >
          <div className="mtt-row mtt-time">{tooltip.timestamp}</div>
          <div className="mtt-row"><span className="mtt-k">SPD</span><span className="mtt-v">{tooltip.speed}</span></div>
          <div className="mtt-row"><span className="mtt-k">HDG</span><span className="mtt-v">{tooltip.heading}</span></div>
          <div className="mtt-row"><span className="mtt-k">1σ</span><span className="mtt-v">{tooltip.uncertainty}</span></div>
        </div>
      )}

      {/* §3.8 Recenter pill — only visible when user has panned away */}
      {userPanned && (
        <button
          className="map-recenter-pill"
          onClick={handleRecenter}
          title="Return camera to vehicle"
        >
          ⊕ RECENTER
        </button>
      )}

      {/* Floating map controls */}
      <div className="map-floating-box">
        <div className="map-btn-row">
          <button
            className={`map-ctrl-btn ${autoFollow && !userPanned ? "active" : ""}`}
            onClick={handleToggleAutoFollow}
          >
            FOLLOW
          </button>
          <button className="map-ctrl-btn" onClick={handleFitRoute}>FIT ROUTE</button>
        </div>
        <div className="map-btn-row">
          <button className={`map-ctrl-btn ${tileStyle === "dark"     ? "active" : ""}`} onClick={() => setTileStyle("dark")}>DARK</button>
          <button className={`map-ctrl-btn ${tileStyle === "streets"  ? "active" : ""}`} onClick={() => setTileStyle("streets")}>STREETS</button>
          <button className={`map-ctrl-btn ${tileStyle === "satellite"? "active" : ""}`} onClick={() => setTileStyle("satellite")}>SAT</button>
        </div>
      </div>

      {/* Zoom controls */}
      <div className="map-zoom-controls">
        <button className="map-zoom-btn" onClick={handleZoomIn}  title="Zoom In">+</button>
        <button className="map-zoom-btn" onClick={handleZoomOut} title="Zoom Out">−</button>
      </div>
    </div>
  );
};
