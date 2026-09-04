import groundTruthData from '../data/ground_truth.json';
import gnssOnlyData from '../data/gnss_only.json';
import fusedOutputData from '../data/fused_output.json';
import smoothedOutputData from '../data/smoothed_output.json';
import { useDashboardContext } from '../context/DashboardContext';

export interface TrajectoryPoint {
  x: number;
  y: number;
  lat?: number;
  lon?: number;
  t: number;
  // Present only on fused_output points (real EKF data, see
  // backend/export_frontend_data.py):
  status?: 'healthy' | 'degraded' | 'outage' | 'unavailable';
  uncertainty?: number;
  velocity?: number;
  heading?: number;
}

// Pre-process GNSS data to linearly interpolate ZOH (1Hz staggering) for smooth 100Hz playback
const rawGnss = gnssOnlyData as TrajectoryPoint[];
const PRECOMPUTED_GNSS = [...rawGnss];
let lastAnchorIdx = 0;
for (let i = 1; i < rawGnss.length; i++) {
  if (rawGnss[i].x !== rawGnss[lastAnchorIdx].x || rawGnss[i].y !== rawGnss[lastAnchorIdx].y || i === rawGnss.length - 1) {
    const p1 = rawGnss[lastAnchorIdx];
    const p2 = rawGnss[i];
    const steps = i - lastAnchorIdx;
    
    // Only interpolate normal 1Hz gaps (~100 points). If gap is huge (outage), let it stay stuck to reflect signal loss.
    if (steps <= 200) {
      for (let j = lastAnchorIdx + 1; j < i; j++) {
        const fraction = (j - lastAnchorIdx) / steps;
        PRECOMPUTED_GNSS[j] = {
          ...PRECOMPUTED_GNSS[j],
          x: p1.x + (p2.x - p1.x) * fraction,
          y: p1.y + (p2.y - p1.y) * fraction,
          lat: p1.lat !== undefined && p2.lat !== undefined ? p1.lat + (p2.lat - p1.lat) * fraction : p1.lat,
          lon: p1.lon !== undefined && p2.lon !== undefined ? p1.lon + (p2.lon - p1.lon) * fraction : p1.lon,
        };
      }
    }
    lastAnchorIdx = i;
  }
}

export const useTrajectoryData = () => {
  const { progress } = useDashboardContext();
  const gt = groundTruthData as TrajectoryPoint[];
  const fused = fusedOutputData as TrajectoryPoint[];
  const smoothed = smoothedOutputData as TrajectoryPoint[];
  const gnss = PRECOMPUTED_GNSS;

  // All three arrays are now the SAME length and time-aligned by
  // export_frontend_data.py (aligned to fused_output's time grid),
  // so a single shared index is safe to use across all three —
  // this was NOT true of the raw backend exports before the adapter.
  const currentIndex = Math.max(0, Math.floor(gt.length * progress) - 1);

  return {
    gt,
    gnss,
    fused,
    smoothed,
    currentIndex,
    currentGnssPos: gnss[currentIndex],
    currentFusedPos: fused[currentIndex],
    currentSmoothedPos: smoothed[currentIndex],
  };
};
