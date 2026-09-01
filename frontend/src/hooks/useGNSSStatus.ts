import { useDashboardContext } from '../context/DashboardContext';
import { useTrajectoryData } from './useTrajectoryData';

// Real outage window for the S3b 60s scenario (200s-260s of 681.1s total),
// from backend/export_frontend_data.py. Display-only constants for
// TimelineSlider's outage band; outage detection below reads real per-point
// status, not these.
export const OUTAGE_START = 0.293643;
export const OUTAGE_END = 0.381735;
export const TOTAL_DURATION = 681.1;

// How long (as progress fraction) "GNSS REACQUIRED" shows after the real
// outage ends before settling back to "GNSS AVAILABLE". 0.05 ≈ 34 s.
const REACQUIRED_WINDOW = 0.05;

export const useGNSSStatus = () => {
  const { simulateOutage, manualOutageStart, progress } = useDashboardContext();
  const { fused, currentIndex, currentFusedPos } = useTrajectoryData();

  const realStatus = currentFusedPos?.status ?? 'healthy';
  const realOutage = realStatus === 'outage' || realStatus === 'unavailable';

  const isOutage = simulateOutage ? true : realOutage;

  // "REACQUIRED" only makes sense just AFTER an outage — not any healthy
  // moment (the old logic showed it at playback start, before any outage).
  const isRecovered =
    !simulateOutage &&
    realStatus === 'healthy' &&
    progress > OUTAGE_END &&
    progress <= OUTAGE_END + REACQUIRED_WINDOW;

  const uncertainty = currentFusedPos?.uncertainty ?? 0;
  const currentVelocity = (currentFusedPos?.velocity ?? 0) * 3.6; // m/s -> km/h

  const rawHeading = currentFusedPos?.heading ?? 0;
  const normalized = ((rawHeading % 360) + 360) % 360;
  const currentHeading = Math.round(normalized * 10) / 10; // fixes 38.139999999999986°

  const aerisError = Math.sqrt(Math.max(0, uncertainty));
  const gnssError = isOutage ? aerisError * 3 : aerisError;

  const dt = fused.length > 1 ? TOTAL_DURATION / (fused.length - 1) : 0.1;

  // Outage timer: manual override gets a REAL elapsed timer from the click
  // moment; recorded outages walk the real per-point status as before.
  let outageTime = 0;
  if (simulateOutage && manualOutageStart !== null) {
    outageTime = Math.max(0, (progress - manualOutageStart) * TOTAL_DURATION);
  } else if (realOutage && fused.length) {
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
