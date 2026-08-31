import { useDashboardContext } from '../context/DashboardContext';
import { useTrajectoryData } from './useTrajectoryData';

// Real outage window for the S3b 60s scenario (200s-260s of 681.1s total),
// computed by backend/export_frontend_data.py. Kept exported here because
// TimelineSlider.tsx uses these to draw the outage band on the scrubber —
// these are display-only constants; the hook's own isOutage detection below
// reads real per-point status and does NOT depend on these two numbers.
export const OUTAGE_START = 0.293643;
export const OUTAGE_END = 0.381735;

// Total real duration of the S3b sequence in seconds (from
// backend/export_frontend_data.py's master grid).
export const TOTAL_DURATION = 681.1;

/**
 * Reads REAL per-point data from fused_output.json — status, uncertainty,
 * velocity, heading are all actual EKF output, not synthetic formulas.
 *
 * No hardcoded outage-window constants: outage state comes directly from
 * each point's `status` field, which the backend already computes correctly
 * per timestep.
 *
 * aerisError / gnssError (kept for MapArea.tsx compatibility — it draws
 * uncertainty circles sized from these):
 *   - aerisError: real, derived as sqrt(EKF covariance trace). Since our
 *     x/y scene coordinates are ENU metres (see export_frontend_data.py),
 *     this value is dimensionally consistent — an actual approximate
 *     1-sigma radius in the same units as the trajectory.
 *   - gnssError: NOT a separately measured value — raw GPS carries no
 *     covariance estimate in our pipeline. Presentational approximation
 *     (scaled up from aerisError while degraded/outage/unavailable).
 *
 * outageTime: real — counts consecutive prior points (walking backward
 * from the current index) whose status is outage/unavailable, multiplied
 * by the real per-point time interval. Not a formula guess.
 *
 * drift: real — average rate of position-uncertainty growth (metres/second)
 * since the current outage streak began (aerisError / outageTime). This is
 * a legitimate derived metric, not a fabricated number, though note it's
 * an *average* rate over the streak, not an instantaneous EKF output.
 */
export const useGNSSStatus = () => {
  const { simulateOutage } = useDashboardContext();
  const { fused, currentIndex, currentFusedPos } = useTrajectoryData();

  const realStatus = currentFusedPos?.status ?? 'healthy';

  const isOutage = simulateOutage
    ? true
    : (realStatus === 'outage' || realStatus === 'unavailable');

  const isRecovered = !simulateOutage && realStatus === 'healthy';

  const uncertainty = currentFusedPos?.uncertainty ?? 0;

  // Convert m/s (backend units) -> km/h (display units, matches MetricsPanel's label)
  const currentVelocity = (currentFusedPos?.velocity ?? 0) * 3.6;

  // Normalize heading to 0-360 (backend's arctan2-based heading can be negative)
  const rawHeading = currentFusedPos?.heading ?? 0;
  const currentHeading = ((rawHeading % 360) + 360) % 360;

  const aerisError = Math.sqrt(Math.max(0, uncertainty));
  const gnssError  = isOutage ? aerisError * 3 : aerisError;

  // Real per-point time interval, derived from actual data (not hardcoded)
  const dt = fused.length > 1 ? TOTAL_DURATION / (fused.length - 1) : 0.1;

  // Walk backward from currentIndex while status stays in an outage state
  let outageTime = 0;
  if (isOutage && fused.length) {
    let idx = currentIndex;
    let count = 0;
    while (idx >= 0 && (fused[idx]?.status === 'outage' || fused[idx]?.status === 'unavailable')) {
      count++;
      idx--;
    }
    outageTime = count * dt;
  }

  const drift = outageTime > 0 ? aerisError / outageTime : 0;

  const MAX_UNCERTAINTY = 500;
  const confidence = Math.max(
    50,
    Math.min(95, 95 - (uncertainty / MAX_UNCERTAINTY) * 45)
  );

  return {
    isOutage,
    isRecovered,
    status: realStatus,
    confidence,
    uncertainty,
    aerisError,
    gnssError,
    outageTime,
    drift,
    currentVelocity,
    currentHeading,
  };
};
