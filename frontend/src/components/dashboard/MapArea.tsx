import React, { useRef, useEffect, useState, useCallback } from 'react';
import L from 'leaflet';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData, type TrajectoryPoint } from '../../hooks/useTrajectoryData';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { drawTrajectory } from './TrajectoryLayer';
import { drawVehicleMarker } from './VehicleMarker';
import { drawUncertaintyCircle } from './UncertaintyCircle';

type TileStyle = 'dark' | 'streets' | 'satellite';

const TILE_LAYERS: Record<TileStyle, { url: string; attribution: string; maxZoom: number; subdomains?: string[] }> = {
  dark: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
    subdomains: ['a', 'b', 'c'],
  },
  streets: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
    subdomains: ['a', 'b', 'c'],
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
    maxZoom: 19,
  },
};

export const MapArea: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number | null>(null);

  const lastFusedHeadingRef = useRef<number>(0);
  const lastGnssHeadingRef = useRef<number>(0);
  const lastSmoothedHeadingRef = useRef<number>(0);

  const [autoFollow, setAutoFollow] = useState<boolean>(true);
  const [tileStyle, setTileStyle] = useState<TileStyle>('dark');

  const { layers } = useDashboardContext();
  const { gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos } = useTrajectoryData();
  const { isOutage, aerisError, gnssError } = useGNSSStatus();

  // Trajectory geographical bounding box
  const getTrajectoryBounds = useCallback((): L.LatLngBounds | null => {
    const pts = gt.length ? gt : fused;
    const validPts = pts.filter((p) => p.lat !== undefined && p.lon !== undefined);
    if (!validPts.length) return null;

    const lats = validPts.map((p) => p.lat!);
    const lons = validPts.map((p) => p.lon!);
    return L.latLngBounds(
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)]
    );
  }, [gt, fused]);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const initialLat = fused[0]?.lat ?? 52.37045;
    const initialLon = fused[0]?.lon ?? -1.25444;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 16,
      zoomControl: false,
      attributionControl: false,
    });

    const config = TILE_LAYERS[tileStyle];
    tileLayerRef.current = L.tileLayer(config.url, {
      attribution: config.attribution,
      maxZoom: config.maxZoom,
      subdomains: config.subdomains ?? ['a', 'b', 'c'],
    }).addTo(map);

    map.on('dragstart', () => {
      setAutoFollow(false);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [fused, tileStyle]);

  // Handle tile style switching
  useEffect(() => {
    if (!mapRef.current) return;
    if (tileLayerRef.current) {
      mapRef.current.removeLayer(tileLayerRef.current);
    }
    const config = TILE_LAYERS[tileStyle];
    tileLayerRef.current = L.tileLayer(config.url, {
      attribution: config.attribution,
      maxZoom: config.maxZoom,
      subdomains: config.subdomains ?? ['a', 'b', 'c'],
    }).addTo(mapRef.current);
  }, [tileStyle]);

  // Render Trajectory Overlay onto Canvas
  const renderCanvas = useCallback(() => {
    const map = mapRef.current;
    const cv = canvasRef.current;
    if (!map || !cv) return;

    const ctx = cv.getContext('2d');
    if (!ctx) return;

    const size = map.getSize();
    if (cv.width !== size.x || cv.height !== size.y) {
      cv.width = size.x;
      cv.height = size.y;
    }

    ctx.clearRect(0, 0, cv.width, cv.height);

    const toPixel = (lat: number, lon: number): { x: number; y: number } => {
      const pt = map.latLngToContainerPoint([lat, lon]);
      return { x: pt.x, y: pt.y };
    };

    const getPixelRadius = (lat: number, lon: number, radiusMeters: number): number => {
      if (radiusMeters <= 0) return 0;
      const center = map.latLngToContainerPoint([lat, lon]);
      const dLat = radiusMeters / 111320;
      const edge = map.latLngToContainerPoint([lat + dLat, lon]);
      return Math.max(4, Math.abs(center.y - edge.y));
    };

    const getHeadingRad = (
      pos: TrajectoryPoint | undefined,
      prevPos: TrajectoryPoint | undefined,
      refStorage: { current: number }
    ): number => {
      if (pos?.heading !== undefined && !isNaN(pos.heading)) {
        const rad = ((pos.heading - 90) * Math.PI) / 180;
        refStorage.current = rad;
        return rad;
      }
      if (
        pos?.lat !== undefined &&
        pos?.lon !== undefined &&
        prevPos?.lat !== undefined &&
        prevPos?.lon !== undefined
      ) {
        const p1 = toPixel(prevPos.lat, prevPos.lon);
        const p2 = toPixel(pos.lat, pos.lon);
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        if (Math.hypot(dx, dy) > 0.4) {
          const rad = Math.atan2(dy, dx);
          refStorage.current = rad;
          return rad;
        }
      }
      return refStorage.current;
    };

    // ── 1. Full Reference Ground Truth Route (Grey dashed) ──────
    if (layers.gt && gt.length > 1) {
      const allGtPixels: { x: number; y: number }[] = [];
      for (let i = 0; i < gt.length; i++) {
        if (gt[i].lat !== undefined && gt[i].lon !== undefined) {
          allGtPixels.push(toPixel(gt[i].lat!, gt[i].lon!));
        }
      }
      drawTrajectory(ctx, allGtPixels, '#5A5A64', 2.0, true);
    }

    // ── 2. Traveled GNSS Trajectory (Cyan #2DD4BF) ───────────────
    if (layers.gnss && gnss.length > 1) {
      const gnssPixels: { x: number; y: number }[] = [];
      const endIdx = Math.min(currentIndex, gnss.length - 1);
      for (let i = 0; i <= endIdx; i++) {
        if (gnss[i].lat !== undefined && gnss[i].lon !== undefined) {
          gnssPixels.push(toPixel(gnss[i].lat!, gnss[i].lon!));
        }
      }
      if (gnssPixels.length > 1) {
        drawTrajectory(ctx, gnssPixels, '#2DD4BF', 2.2, false);
      }
    }

    // ── 3. Traveled AERIS ES-EKF Trajectory (Orange #F0801E) ─────
    if (layers.fused && fused.length > 1) {
      const fusedPixels: { x: number; y: number }[] = [];
      const endIdx = Math.min(currentIndex, fused.length - 1);
      for (let i = 0; i <= endIdx; i++) {
        if (fused[i].lat !== undefined && fused[i].lon !== undefined) {
          fusedPixels.push(toPixel(fused[i].lat!, fused[i].lon!));
        }
      }
      if (fusedPixels.length > 1) {
        // Blended line (Teal outside outage, Orange during outage)
        drawTrajectory(ctx, fusedPixels, isOutage ? '#F0801E' : '#2DD4BF', isOutage ? 3.0 : 2.4, false);
      }
    }

    // ── 4. Traveled Smoothed RTS Trajectory (Purple #A855F7) ────
    if (layers.smoothed && smoothed && smoothed.length > 1) {
      const smoothedPixels: { x: number; y: number }[] = [];
      const endIdx = Math.min(currentIndex, smoothed.length - 1);
      for (let i = 0; i <= endIdx; i++) {
        if (smoothed[i].lat !== undefined && smoothed[i].lon !== undefined) {
          smoothedPixels.push(toPixel(smoothed[i].lat!, smoothed[i].lon!));
        }
      }
      if (smoothedPixels.length > 1) {
        drawTrajectory(ctx, smoothedPixels, '#A855F7', 2.8, false);
      }
    }

    // Count how many vehicle layers are actively toggled
    const activeCount =
      (layers.gnss ? 1 : 0) + (layers.fused ? 1 : 0) + (layers.smoothed ? 1 : 0);

    // ── 5A. Render GNSS Raw Vehicle Arrow ────────────────────────
    if (layers.gnss && currentGnssPos && currentGnssPos.lat !== undefined && currentGnssPos.lon !== undefined) {
      const pt = toPixel(currentGnssPos.lat, currentGnssPos.lon);
      const prev = currentIndex > 0 ? gnss[currentIndex - 1] : undefined;
      const h = getHeadingRad(currentGnssPos, prev, lastGnssHeadingRef);
      const gnssColor = isOutage ? '#E5484D' : '#2DD4BF';

      if (isOutage) {
        const rPx = getPixelRadius(currentGnssPos.lat, currentGnssPos.lon, gnssError);
        drawUncertaintyCircle(ctx, pt.x, pt.y, rPx, 'rgba(229, 72, 77, 0.12)');
      }

      drawVehicleMarker(
        ctx,
        pt.x,
        pt.y,
        h,
        gnssColor,
        activeCount > 1 ? 'GNSS' : undefined,
        isOutage,
        !layers.fused && !layers.smoothed // Halo only if primary
      );
    }

    // ── 5B. Render RTS Smoothed Vehicle Arrow ───────────────────
    if (layers.smoothed && currentSmoothedPos && currentSmoothedPos.lat !== undefined && currentSmoothedPos.lon !== undefined) {
      const pt = toPixel(currentSmoothedPos.lat, currentSmoothedPos.lon);
      const prev = currentIndex > 0 ? smoothed[currentIndex - 1] : undefined;
      const h = getHeadingRad(currentSmoothedPos, prev, lastSmoothedHeadingRef);

      drawVehicleMarker(
        ctx,
        pt.x,
        pt.y,
        h,
        '#A855F7',
        activeCount > 1 ? 'RTS' : undefined,
        false,
        !layers.fused // Halo if fused is off
      );
    }

    // ── 5C. Render AERIS ES-EKF Vehicle Arrow (Primary Solution) ─
    if (layers.fused && currentFusedPos && currentFusedPos.lat !== undefined && currentFusedPos.lon !== undefined) {
      const pt = toPixel(currentFusedPos.lat, currentFusedPos.lon);
      const prev = currentIndex > 0 ? fused[currentIndex - 1] : undefined;
      const h = getHeadingRad(currentFusedPos, prev, lastFusedHeadingRef);
      const fusedColor = isOutage ? '#F0801E' : '#2DD4BF';

      if (isOutage) {
        const rPx = getPixelRadius(currentFusedPos.lat, currentFusedPos.lon, aerisError);
        drawUncertaintyCircle(ctx, pt.x, pt.y, rPx, 'rgba(240, 128, 30, 0.20)');
      }

      drawVehicleMarker(
        ctx,
        pt.x,
        pt.y,
        h,
        fusedColor,
        activeCount > 1 ? 'ES-EKF' : undefined,
        isOutage,
        true // Always prominent halo
      );
    }
  }, [gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos, layers, isOutage, aerisError, gnssError]);

  // Continuous animation loop for beacon pulse wave & live rendering
  useEffect(() => {
    const loop = () => {
      renderCanvas();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [renderCanvas]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    map.on('move', renderCanvas);
    map.on('zoom', renderCanvas);
    map.on('viewreset', renderCanvas);

    return () => {
      map.off('move', renderCanvas);
      map.off('zoom', renderCanvas);
      map.off('viewreset', renderCanvas);
    };
  }, [renderCanvas]);

  // Auto-follow vehicle camera (Priority: Fused -> Smoothed -> GNSS)
  useEffect(() => {
    const map = mapRef.current;
    if (map && autoFollow) {
      let pos = null;
      if (layers.fused) pos = currentFusedPos;
      else if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.gnss) pos = currentGnssPos;

      if (pos && pos.lat !== undefined && pos.lon !== undefined) {
        map.panTo([pos.lat, pos.lon], { animate: false });
      }
    }
    renderCanvas();
  }, [currentIndex, autoFollow, currentFusedPos, currentGnssPos, currentSmoothedPos, layers, renderCanvas]);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
        renderCanvas();
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, [renderCanvas]);

  const handleFitRoute = () => {
    setAutoFollow(false);
    const bounds = getTrajectoryBounds();
    if (mapRef.current && bounds) {
      mapRef.current.fitBounds(bounds, { padding: [40, 40], animate: true });
    }
  };

  const handleToggleAutoFollow = () => {
    const next = !autoFollow;
    setAutoFollow(next);
    if (next && mapRef.current) {
      let pos = null;
      if (layers.fused) pos = currentFusedPos;
      else if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.gnss) pos = currentGnssPos;

      if (pos && pos.lat !== undefined && pos.lon !== undefined) {
        mapRef.current.setView([pos.lat, pos.lon], 16, { animate: true });
      }
    }
  };

  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();

  return (
    <div className="map-viewport-container">
      {/* Base Leaflet Map */}
      <div
        id="leafletMap"
        ref={mapContainerRef}
        className={`portal-leaflet-map tile-${tileStyle}`}
      />

      {/* Trajectory & vehicle canvas overlay */}
      <canvas
        id="mainCanvas"
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />

      {/* Small Compact Floating Map Control Box (Top-Right) */}
      <div className="map-floating-box">
        <div className="map-btn-row">
          <button
            className={`map-ctrl-btn ${autoFollow ? 'active' : ''}`}
            onClick={handleToggleAutoFollow}
          >
            FOLLOW
          </button>
          <button
            className="map-ctrl-btn"
            onClick={handleFitRoute}
          >
            FIT ROUTE
          </button>
        </div>
        <div className="map-btn-row">
          <button
            className={`map-ctrl-btn ${tileStyle === 'dark' ? 'active' : ''}`}
            onClick={() => setTileStyle('dark')}
          >
            DARK
          </button>
          <button
            className={`map-ctrl-btn ${tileStyle === 'streets' ? 'active' : ''}`}
            onClick={() => setTileStyle('streets')}
          >
            STREETS
          </button>
          <button
            className={`map-ctrl-btn ${tileStyle === 'satellite' ? 'active' : ''}`}
            onClick={() => setTileStyle('satellite')}
          >
            SAT
          </button>
        </div>
      </div>

      {/* Separate + / − Zoom Controls on Map */}
      <div className="map-zoom-controls">
        <button className="map-zoom-btn" onClick={handleZoomIn} title="Zoom In">+</button>
        <button className="map-zoom-btn" onClick={handleZoomOut} title="Zoom Out">−</button>
      </div>
    </div>
  );
};
