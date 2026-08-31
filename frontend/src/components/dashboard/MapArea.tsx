import React, { useRef, useEffect } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { drawTrajectory } from './TrajectoryLayer';
import { drawVehicleMarker } from './VehicleMarker';
import { drawUncertaintyCircle } from './UncertaintyCircle';

export const MapArea: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { layers } = useDashboardContext();
  const { gt, gnss, fused, currentIndex, currentGnssPos, currentFusedPos } = useTrajectoryData();
  const { isOutage, aerisError, gnssError } = useGNSSStatus();

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d');
    if (!ctx) return;

    let w = cv.width, h = cv.height;
    const resize = () => {
      w = cv.width = cv.offsetWidth;
      h = cv.height = cv.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Draw loop (we tie it to component updates since state changes via requestAnimationFrame in usePlayback)
    // For optimal performance, the draw function could be completely detached from React state and read refs directly,
    // but this hybrid approach works fine since progress changes ~60fps anyway.
    
    ctx.clearRect(0, 0, w, h);
    
    // Transform coordinates slightly if needed to center on screen (optional, assuming data is pre-scaled or we scale it here)
    // The generated data has X around 12% and Y around 82%, we'll just draw it directly.

    // Find bounding box to center trajectory
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    gt.forEach(p => {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    });

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const padding = 100;
    const scale = Math.min((w - padding * 2) / (maxX - minX), (h - padding * 2) / (maxY - minY));

    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.scale(scale, scale);
    ctx.translate(-cx, -cy);

    // Draw past trajectories up to currentIndex
    if (layers.gt) drawTrajectory(ctx, gt.slice(0, currentIndex + 1), '#26262B', 1 / scale, true);
    if (layers.gnss) drawTrajectory(ctx, gnss.slice(0, currentIndex + 1), '#2DD4BF', 2 / scale, false);
    if (layers.fused && isOutage) {
      const outageStartIndex = fused.findIndex((p) => p.status === 'outage' || p.status === 'unavailable');
      if (currentIndex >= outageStartIndex) {
         drawTrajectory(ctx, fused.slice(outageStartIndex, currentIndex + 1), '#F0801E', 2 / scale, false);
      }
    }

    // Determine current position based on layers
    let x = currentFusedPos?.x || 0;
    let y = currentFusedPos?.y || 0;
    let heading = 0;

    if (layers.fused) {
      x = currentFusedPos?.x || 0;
      y = currentFusedPos?.y || 0;
    } else if (layers.gnss) {
      x = currentGnssPos?.x || 0;
      y = currentGnssPos?.y || 0;
    }

    if (currentIndex > 0) {
      const prev = layers.fused ? fused[currentIndex - 1] : gnss[currentIndex - 1];
      if (prev) {
        heading = Math.atan2(y - prev.y, x - prev.x);
      }
    }

    // Draw uncertainties
   if (layers.gnss && isOutage && currentGnssPos) {
      drawUncertaintyCircle(ctx, currentGnssPos.x, currentGnssPos.y, gnssError * 2, 'rgba(45,212,191,0.15)');
    }
    if (layers.fused && isOutage && currentFusedPos) {
      drawUncertaintyCircle(ctx, currentFusedPos.x, currentFusedPos.y, aerisError * 2, 'rgba(240,128,30,0.15)');
    }

    // Draw vehicle marker - inverse scale so it stays a constant size visually
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(1/scale, 1/scale);
    ctx.translate(-x, -y);
    const color = (isOutage && layers.fused) ? '#F0801E' : (isOutage && !layers.fused ? '#E5484D' : '#2DD4BF');
    drawVehicleMarker(ctx, x, y, heading, color);
    ctx.restore();

    ctx.restore();

    return () => window.removeEventListener('resize', resize);
  }); // runs every render, driven by `progress` context changes

  return (
    <div className="portal-canvas-wrap">
      <div className="grid-overlay"></div>
      <canvas id="mainCanvas" ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }}></canvas>
    </div>
  );
};
