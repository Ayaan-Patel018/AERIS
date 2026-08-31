import { useDashboardContext } from '../context/DashboardContext';

export const OUTAGE_START = 0.35;
export const OUTAGE_END = 0.65;
export const TOTAL_DURATION = 60;

export const useGNSSStatus = () => {
  const { progress, simulateOutage } = useDashboardContext();
  
  const effectiveOS = simulateOutage ? 0 : OUTAGE_START;
  const effectiveOE = simulateOutage ? progress : OUTAGE_END;

  const isOutage = progress >= effectiveOS && progress <= effectiveOE;
  const isRecovered = !simulateOutage && progress > OUTAGE_END;

  // Time elapsed in outage
  const outageTime = isOutage ? (progress - effectiveOS) * TOTAL_DURATION : 0;
  
  // Confidence goes down as outage goes on
  const confidence = isOutage ? Math.max(58, 94 - outageTime * 0.45) : 94;
  
  // Drift and Position Error
  const drift = isOutage ? outageTime * 0.009 : 0;
  const aerisError = isOutage ? outageTime * 0.038 : 0;
  const gnssError = isOutage ? outageTime * 0.75 : 0;
  
  // Simulated velocity/heading readouts
  const currentVelocity = 33 + Math.sin(progress * 22) * 9;
  const currentHeading = Math.floor(38 + progress * 32);

  return {
    isOutage,
    isRecovered,
    outageTime,
    confidence,
    drift,
    aerisError,
    gnssError,
    currentVelocity,
    currentHeading
  };
};
