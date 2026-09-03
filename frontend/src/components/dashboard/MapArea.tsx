import React, { useRef, useEffect, useState, useCallback } from 'react';
import L from 'leaflet';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { drawTrajectory } from './TrajectoryLayer';
import { drawVehicleMarker } from './VehicleMarker';
import { drawUncertaintyCircle } from './UncertaintyCircle';
import { LocateFixed, Maximize2, Plus, Minus, Compass } from 'lucide-react';

type TileStyle = 'dark' | 'streets' | 'satellite';

const TILE_LAYERS: Record<TileStyle, { url: string; attribution: string; maxZoom: number; subdomains?: string[] }> = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 20,
    subdomains: ['a', 'b', 'c', 'd'],
  },
  streets: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    subdomains: ['a', 'b', 'c'],
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 19,
  },
};

export const MapArea: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastHeadingRef = useRef<number>(0);

  const [autoFollow, setAutoFollow] = useState<boolean>(true);
  const [tileStyle, setTileStyle] = useState<TileStyle>('dark');

  const { layers } = useDashboardContext();
  const { gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos } = useTrajectoryData();
  const { isOutage, aerisError, gnssError } = useGNSSStatus();

  // ── Calculate trajectory bounding box for initial fitting ──────────────
  const getTrajectoryBounds = useCallback((): L.LatLngBounds | null => {
    let minLat = 90, maxLat = -90, minLon = 180, maxLon = -180;
    let hasPoints = false;
    for (let i = 0; i < gt.length; i++) {
      const p = gt[i];
      if (p.lat !== undefined && p.lon !== undefined) {
        if (p.lat < minLat) minLat = p.lat;
        if (p.lat > maxLat) maxLat = p.lat;
        if (p.lon < minLon) minLon = p.lon;
        if (p.lon > maxLon) maxLon = p.lon;
        hasPoints = true;
      }
    }
    if (!hasPoints) return null;
    return L.latLngBounds([minLat, minLon], [maxLat, maxLon]);
  }, [gt]);

  // ── Initialize Leaflet map ──────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapRef.current) return; // Prevent double initialization

    const initialBounds = getTrajectoryBounds();
    const center: [number, number] = initialBounds
      ? [initialBounds.getCenter().lat, initialBounds.getCenter().lng]
      : [52.374, -1.258];

    const map = L.map(mapContainerRef.current, {
      center,
      zoom: 16,
      zoomControl: false,
      attributionControl: true,
      fadeAnimation: true,
      zoomAnimation: true,
    });

    // Add selected tile layer
    const config = TILE_LAYERS[tileStyle];
    tileLayerRef.current = L.tileLayer(config.url, {
      attribution: config.attribution,
      maxZoom: config.maxZoom,
      subdomains: config.subdomains ?? ['a', 'b', 'c'],
    }).addTo(map);

    // Fit bounds on start
    if (initialBounds) {
      map.fitBounds(initialBounds, { padding: [50, 50] });
    }

    // When user drags map manually, disable auto-follow
    map.on('dragstart', () => {
      setAutoFollow(false);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [getTrajectoryBounds]);

  // ── Handle tile style switching ─────────────────────────────────────────
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

  // ── Render Trajectory Overlay onto Canvas ────────────────────────────────
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

    // 1. Draw Full Reference Ground Truth Route (Muted dashed road trace)
    if (layers.gt && gt.length > 1) {
      const allGtPixels: { x: number; y: number }[] = [];
      for (let i = 0; i < gt.length; i++) {
        if (gt[i].lat !== undefined && gt[i].lon !== undefined) {
          allGtPixels.push(toPixel(gt[i].lat!, gt[i].lon!));
        }
      }
      drawTrajectory(ctx, allGtPixels, '#3A3A42', 1.8, true);
    }

    // 2. Draw Traveled GNSS Trajectory (Glowing Cyan #2DD4BF)
    if (layers.gnss && gnss.length > 1) {
      const gnssPixels: { x: number; y: number }[] = [];
      const endIdx = Math.min(currentIndex, gnss.length - 1);
      for (let i = 0; i <= endIdx; i++) {
        if (gnss[i].lat !== undefined && gnss[i].lon !== undefined) {
          gnssPixels.push(toPixel(gnss[i].lat!, gnss[i].lon!));
        }
      }
      drawTrajectory(ctx, gnssPixels, '#2DD4BF', 2.5, false);
    }

    // 3. Draw Fused EKF Dead Reckoning Trajectory during Outage (Safety Orange #F0801E)
    if (layers.fused && isOutage && fused.length > 1) {
      const outageStartIndex = fused.findIndex((p) => p.status === 'outage' || p.status === 'unavailable');
      if (outageStartIndex !== -1 && currentIndex >= outageStartIndex) {
        const fusedPixels: { x: number; y: number }[] = [];
        const endIdx = Math.min(currentIndex, fused.length - 1);
        for (let i = outageStartIndex; i <= endIdx; i++) {
          if (fused[i].lat !== undefined && fused[i].lon !== undefined) {
            fusedPixels.push(toPixel(fused[i].lat!, fused[i].lon!));
          }
        }
        drawTrajectory(ctx, fusedPixels, '#F0801E', 3.0, false);
      }
    }

    // 4. Draw Smoothed RTS Trajectory (Purple #A855F7)
    if (layers.smoothed && smoothed && smoothed.length > 1) {
      const smoothedPixels: { x: number; y: number }[] = [];
      const endIdx = Math.min(currentIndex, smoothed.length - 1);
      for (let i = 0; i <= endIdx; i++) {
        if (smoothed[i].lat !== undefined && smoothed[i].lon !== undefined) {
          smoothedPixels.push(toPixel(smoothed[i].lat!, smoothed[i].lon!));
        }
      }
      drawTrajectory(ctx, smoothedPixels, '#A855F7', 3.0, false);
    }

    // Determine current position
    let curPos = null;
    let vehicleColor = '#2DD4BF';

    if (layers.smoothed && currentSmoothedPos && currentSmoothedPos.lat !== undefined && currentSmoothedPos.lon !== undefined) {
      curPos = currentSmoothedPos;
      vehicleColor = '#A855F7';
    } else if (layers.fused && currentFusedPos && currentFusedPos.lat !== undefined && currentFusedPos.lon !== undefined) {
      curPos = currentFusedPos;
      vehicleColor = isOutage ? '#F0801E' : '#2DD4BF';
    } else if (layers.gnss && currentGnssPos && currentGnssPos.lat !== undefined && currentGnssPos.lon !== undefined) {
      curPos = currentGnssPos;
      vehicleColor = isOutage ? '#E5484D' : '#2DD4BF';
    }

    if (!curPos) return;

    const curPt = toPixel(curPos.lat, curPos.lon);

    // Calculate heading from recent movement
    if (currentIndex > 0) {
      let prevPos = null;
      if (layers.smoothed) prevPos = smoothed[currentIndex - 1];
      else if (layers.fused) prevPos = fused[currentIndex - 1];
      else if (layers.gnss) prevPos = gnss[currentIndex - 1];
      
      if (prevPos && prevPos.lat !== undefined && prevPos.lon !== undefined) {
        const prevPt = toPixel(prevPos.lat, prevPos.lon);
        const dx = curPt.x - prevPt.x;
        const dy = curPt.y - prevPt.y;
        if (Math.hypot(dx, dy) > 0.4) {
          lastHeadingRef.current = Math.atan2(dy, dx);
        }
      }
    }
    const heading = lastHeadingRef.current;

    // Helper: calculate physical radius in screen pixels
    const getPixelRadius = (lat: number, lon: number, radiusMeters: number): number => {
      if (radiusMeters <= 0) return 0;
      const center = map.latLngToContainerPoint([lat, lon]);
      const dLat = radiusMeters / 111320; // 1 degree lat ≈ 111.32 km
      const edge = map.latLngToContainerPoint([lat + dLat, lon]);
      return Math.max(3, Math.abs(center.y - edge.y));
    };

    // Draw GNSS Uncertainty Circle
    if (layers.gnss && isOutage && currentGnssPos && currentGnssPos.lat !== undefined && currentGnssPos.lon !== undefined) {
      const gnssCenter = toPixel(currentGnssPos.lat, currentGnssPos.lon);
      const gnssRadiusPx = getPixelRadius(currentGnssPos.lat, currentGnssPos.lon, gnssError);
      drawUncertaintyCircle(ctx, gnssCenter.x, gnssCenter.y, gnssRadiusPx, 'rgba(45, 212, 191, 0.15)');
    }

    // Draw Fused Uncertainty Circle
    if (layers.fused && isOutage && currentFusedPos && currentFusedPos.lat !== undefined && currentFusedPos.lon !== undefined) {
      const fusedRadiusPx = getPixelRadius(currentFusedPos.lat, currentFusedPos.lon, aerisError);
      drawUncertaintyCircle(ctx, curPt.x, curPt.y, fusedRadiusPx, 'rgba(240, 128, 30, 0.15)');
    }

    // Draw Vehicle Marker with active beacon pulse during outage
    drawVehicleMarker(ctx, curPt.x, curPt.y, heading, vehicleColor, isOutage);
  }, [gt, gnss, fused, smoothed, currentIndex, currentGnssPos, currentFusedPos, currentSmoothedPos, layers, isOutage, aerisError, gnssError]);

  // ── Sync canvas whenever map moves, zooms, or renders ───────────────────
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

  // ── Camera Auto-Follow & Playback Frame Update ───────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (map && autoFollow) {
      let pos = null;
      if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.fused) pos = currentFusedPos;
      else if (layers.gnss) pos = currentGnssPos;

      if (pos && pos.lat !== undefined && pos.lon !== undefined) {
        // Keep camera centered on vehicle during playback
        map.setView([pos.lat, pos.lon], map.getZoom(), { animate: false });
      }
    }
    renderCanvas();
  }, [currentIndex, autoFollow, currentFusedPos, currentGnssPos, currentSmoothedPos, layers, renderCanvas]);

  // ── Container Resize Handler ────────────────────────────────────────────
  useEffect(() => {
    const handleResize = () => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
        renderCanvas();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderCanvas]);

  // ── HUD Actions ─────────────────────────────────────────────────────────
  const handleFitRoute = () => {
    setAutoFollow(false);
    const bounds = getTrajectoryBounds();
    if (mapRef.current && bounds) {
      mapRef.current.fitBounds(bounds, { padding: [60, 60], animate: true });
    }
  };

  const handleToggleAutoFollow = () => {
    const next = !autoFollow;
    setAutoFollow(next);
    if (next && mapRef.current) {
      let pos = null;
      if (layers.smoothed) pos = currentSmoothedPos;
      else if (layers.fused) pos = currentFusedPos;
      else if (layers.gnss) pos = currentGnssPos;

      if (pos && pos.lat !== undefined && pos.lon !== undefined) {
        mapRef.current.panTo([pos.lat, pos.lon], { animate: true });
      }
    }
  };

  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();

  return (
    <div className="portal-canvas-wrap">
      {/* Real OpenStreetMap / CartoDB Tile Layer underneath */}
      <div
        id="leafletMap"
        ref={mapContainerRef}
        className="portal-leaflet-map"
      />

      {/* Subtle coordinate grid overlay */}
      <div className="grid-overlay" />

      {/* Trajectory & vehicle canvas overlay */}
      <canvas
        id="mainCanvas"
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />

      {/* Top-Right Technical Orientation Compass Rose */}
      <div className="map-compass-hud">
        <div className="compass-reticle">
          <div className="compass-needle-n"></div>
          <span className="compass-n-label">N</span>
        </div>
        <div className="compass-meta">
          <span className="compass-datum">WGS-84</span>
          <span className="compass-grid">ENU 10Hz</span>
        </div>
      </div>

      {/* Floating Solid HUD Controls */}
      <div className="map-hud-controls">
        <div className="map-hud-group">
          <button
            className={`map-hud-btn ${autoFollow ? 'active' : ''}`}
            onClick={handleToggleAutoFollow}
            title={autoFollow ? 'Auto-follow active' : 'Click to follow vehicle'}
          >
            <LocateFixed size={13} className="hud-ic" />
            <span>FOLLOW</span>
          </button>
          <button
            className="map-hud-btn"
            onClick={handleFitRoute}
            title="Fit entire trajectory to screen"
          >
            <Maximize2 size={12} className="hud-ic" />
            <span>FIT ROUTE</span>
          </button>
        </div>

        <div className="map-hud-group">
          <button
            className={`map-hud-btn ${tileStyle === 'dark' ? 'active' : ''}`}
            onClick={() => setTileStyle('dark')}
          >
            DARK
          </button>
          <button
            className={`map-hud-btn ${tileStyle === 'streets' ? 'active' : ''}`}
            onClick={() => setTileStyle('streets')}
          >
            STREETS
          </button>
          <button
            className={`map-hud-btn ${tileStyle === 'satellite' ? 'active' : ''}`}
            onClick={() => setTileStyle('satellite')}
          >
            SAT
          </button>
        </div>

        <div className="map-hud-group">
          <button
            className="map-hud-btn map-hud-icon-btn"
            onClick={handleZoomIn}
            title="Zoom In"
          >
            <Plus size={13} />
          </button>
          <button
            className="map-hud-btn map-hud-icon-btn"
            onClick={handleZoomOut}
            title="Zoom Out"
          >
            <Minus size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};
