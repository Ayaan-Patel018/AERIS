import { useMemo } from 'react';
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
  // Present on fused_output and smoothed_output points (real EKF data):
  status?: 'healthy' | 'degraded' | 'outage' | 'unavailable';
  uncertainty?: number;
  velocity?: number;
  heading?: number;
  // 2×2 East-North covariance block for oriented ellipse renderer:
  // Σ_EN = [[cov_xx, cov_xy],[cov_xy, cov_yy]]  (units: m²)
  // Eigendecomposition → semi-axes and rotation angle of 2σ ellipse.
  cov_xx?: number;   // σ²_EE (East variance)
  cov_yy?: number;   // σ²_NN (North variance)
  cov_xy?: number;   // σ_EN (off-diagonal covariance)
}

function interpolateGnss(rawGnss: TrajectoryPoint[]): TrajectoryPoint[] {
  if (!rawGnss || rawGnss.length === 0) return [];
  const result = [...rawGnss];
  let lastAnchorIdx = 0;
  for (let i = 1; i < rawGnss.length; i++) {
    if (
      rawGnss[i].x !== rawGnss[lastAnchorIdx].x ||
      rawGnss[i].y !== rawGnss[lastAnchorIdx].y ||
      i === rawGnss.length - 1
    ) {
      const p1 = rawGnss[lastAnchorIdx];
      const p2 = rawGnss[i];
      const steps = i - lastAnchorIdx;

      if (steps <= 200) {
        for (let j = lastAnchorIdx + 1; j < i; j++) {
          const fraction = (j - lastAnchorIdx) / steps;
          result[j] = {
            ...result[j],
            x: p1.x + (p2.x - p1.x) * fraction,
            y: p1.y + (p2.y - p1.y) * fraction,
            lat:
              p1.lat !== undefined && p2.lat !== undefined
                ? p1.lat + (p2.lat - p1.lat) * fraction
                : p1.lat,
            lon:
              p1.lon !== undefined && p2.lon !== undefined
                ? p1.lon + (p2.lon - p1.lon) * fraction
                : p1.lon,
          };
        }
      }
      lastAnchorIdx = i;
    }
  }
  return result;
}

const STATIC_RAW_GNSS = gnssOnlyData as TrajectoryPoint[];
const STATIC_INTERPOLATED_GNSS = interpolateGnss(STATIC_RAW_GNSS);

export const useTrajectoryData = () => {
  const { progress, dynamicData } = useDashboardContext();

  const gt = useMemo(() => {
    return (dynamicData?.ground_truth ?? groundTruthData) as TrajectoryPoint[];
  }, [dynamicData]);

  const fused = useMemo(() => {
    return (dynamicData?.fused_output ?? fusedOutputData) as TrajectoryPoint[];
  }, [dynamicData]);

  const smoothed = useMemo(() => {
    if (dynamicData?.smoothed_output) {
      return dynamicData.smoothed_output as TrajectoryPoint[];
    }
    return smoothedOutputData as TrajectoryPoint[];
  }, [dynamicData]);

  const gnss = useMemo(() => {
    if (dynamicData?.gnss_only) {
      return interpolateGnss(dynamicData.gnss_only as TrajectoryPoint[]);
    }
    return STATIC_INTERPOLATED_GNSS;
  }, [dynamicData]);

  const totalPoints = gt.length || fused.length || 1;
  const currentIndex = Math.max(0, Math.min(totalPoints - 1, Math.floor(totalPoints * progress)));

  return {
    gt,
    gnss,
    fused,
    smoothed,
    currentIndex,
    currentGnssPos: gnss[currentIndex] ?? gnss[gnss.length - 1],
    currentFusedPos: fused[currentIndex] ?? fused[fused.length - 1],
    currentSmoothedPos: smoothed[currentIndex] ?? smoothed[smoothed.length - 1],
  };
};
