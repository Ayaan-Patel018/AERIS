import groundTruthData from '../data/ground_truth.json';
import gnssOnlyData from '../data/gnss_only.json';
import fusedOutputData from '../data/fused_output.json';
import { useDashboardContext } from '../context/DashboardContext';

export interface TrajectoryPoint {
  x: number;
  y: number;
  t: number;
  // Present only on fused_output points (real EKF data, see
  // backend/export_frontend_data.py):
  status?: 'healthy' | 'degraded' | 'outage' | 'unavailable';
  uncertainty?: number;
  velocity?: number;
  heading?: number;
}

export const useTrajectoryData = () => {
  const { progress } = useDashboardContext();
  const gt = groundTruthData as TrajectoryPoint[];
  const gnss = gnssOnlyData as TrajectoryPoint[];
  const fused = fusedOutputData as TrajectoryPoint[];

  // All three arrays are now the SAME length and time-aligned by
  // export_frontend_data.py (aligned to fused_output's time grid),
  // so a single shared index is safe to use across all three —
  // this was NOT true of the raw backend exports before the adapter.
  const currentIndex = Math.max(0, Math.floor(gt.length * progress) - 1);

  return {
    gt,
    gnss,
    fused,
    currentIndex,
    currentGnssPos: gnss[currentIndex],
    currentFusedPos: fused[currentIndex],
  };
};
