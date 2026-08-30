import groundTruthData from '../data/ground_truth.json';
import gnssOnlyData from '../data/gnss_only.json';
import fusedOutputData from '../data/fused_output.json';
import { useDashboardContext } from '../context/DashboardContext';

export interface TrajectoryPoint {
  x: number;
  y: number;
  t: number;
}

export const useTrajectoryData = () => {
  const { progress } = useDashboardContext();

  const gt = groundTruthData as TrajectoryPoint[];
  const gnss = gnssOnlyData as TrajectoryPoint[];
  const fused = fusedOutputData as TrajectoryPoint[];

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
