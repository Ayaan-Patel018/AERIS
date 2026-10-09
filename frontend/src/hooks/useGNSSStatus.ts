/**
 * useGNSSStatus.ts
 *
 * GNSS + filter status derived from REAL per-point data only.
 * No hardcoded outage windows, satellite counts, or signal bars.
 * TOTAL_DURATION_S comes from driveMetadata (loaded via LoadingScreen),
 * with a fallback to the known value of 681.1 s for the S3b dataset.
 */
import { useDashboardContext } from "../context/DashboardContext";
import { useTrajectoryData } from "./useTrajectoryData";

// How long (as a fraction of total duration) "GNSS REACQUIRED" shows after
// the last outage point before reverting to "GNSS AVAILABLE". ~34 s at 681 s.
const REACQUIRED_WINDOW_FRAC = 0.05;

export const useGNSSStatus = () => {
  const {
    simulateOutage,
    manualOutageStart,
    progress,
    outageStartSec,
    outageEndSec,
    totalDurationS,
    driveMetadata,
  } = useDashboardContext();

  const { fused, currentIndex, currentFusedPos } = useTrajectoryData();

  // Real status from the per-point data field
  const realStatus = currentFusedPos?.status ?? "healthy";
  const realOutage =
    realStatus === "outage" || realStatus === "unavailable";

  const isOutage = simulateOutage ? true : realOutage;

  // Identify the end of the most recent outage window (in progress fraction)
  // so "REACQUIRED" only fires just after an actual outage, not at boot.
  const lastOutage = driveMetadata?.outage_windows?.at(-1);
  const lastOutageEndFrac = lastOutage
    ? lastOutage.end_t
    : outageEndSec / totalDurationS;

  const isRecovered =
    !simulateOutage &&
    realStatus === "healthy" &&
    progress > lastOutageEndFrac &&
    progress <= lastOutageEndFrac + REACQUIRED_WINDOW_FRAC;

  // Uncertainty (1-sigma, metres) from real data
  const uncertainty = currentFusedPos?.uncertainty ?? 0;
  const aerisError  = Math.sqrt(Math.max(0, uncertainty));

  // Speed: data is m/s, convert to km/h for display
  const currentVelocity = (currentFusedPos?.velocity ?? 0) * 3.6;

  // Heading: degrees, normalised to [0, 360)
  const rawHeading  = currentFusedPos?.heading ?? 0;
  const normalised  = ((rawHeading % 360) + 360) % 360;
  const currentHeading = Math.round(normalised * 10) / 10;

  // Outage elapsed time
  const dt = fused.length > 1 ? totalDurationS / (fused.length - 1) : 0.1;
  let outageTime = 0;
  if (simulateOutage && manualOutageStart !== null) {
    outageTime = Math.max(0, (progress - manualOutageStart) * totalDurationS);
  } else if (realOutage && fused.length) {
    let idx = currentIndex;
    let count = 0;
    while (
      idx >= 0 &&
      (fused[idx]?.status === "outage" || fused[idx]?.status === "unavailable")
    ) {
      count++;
      idx--;
    }
    outageTime = count * dt;
  }

  // Drift velocity (m/s): how fast the uncertainty is growing per second
  const drift = outageTime > 0 ? aerisError / outageTime : 0;

  return {
    isOutage,
    isRecovered,
    status: realStatus,
    uncertainty,
    aerisError,
    outageTime,
    drift,
    currentVelocity,
    currentHeading,
    totalDurationS,
  };
};
