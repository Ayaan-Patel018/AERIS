import groundTruthData from '../data/ground_truth.json';
import gnssOnlyData from '../data/gnss_only.json';
import fusedOutputData from '../data/fused_output.json';
import smoothedOutputData from '../data/smoothed_output.json';
import { useDashboardContext } from '../context/DashboardContext';

// ── ENU origin ───────────────────────────────────────────────────────────────
// The lat/lon anchor used by the backend's latlon_to_enu() flat-Earth formula.
// Read from: print(f"Origin: lat0={lat0:.6f}, lon0={lon0:.6f}") in export_frontend_data.py
// Full-precision values from actual script output (not the rounded print):
export const LAT0 = 52.37044988688084;
export const LON0 = -1.254437787155459;

const R    = 6_371_000.0;          // Earth radius in metres (matches backend)
const D2R  = Math.PI / 180;
const COS0 = Math.cos(LAT0 * D2R); // precomputed — constant for this dataset

/**
 * Convert local ENU (east=x, north=y) in metres back to geographic lat/lon.
 * Exact inverse of backend's latlon_to_enu() flat-Earth approximation.
 * Valid for sequences < ~50 km from origin — the Rugby S3b sequence is ~0.7 km.
 */
export function enuToLatLng(x: number, y: number): { lat: number; lon: number } {
  return {
    lat: LAT0 + (y / R) / D2R,
    lon: LON0 + (x / R) / (D2R * COS0),
  };
}

// ── TrajectoryPoint interface ─────────────────────────────────────────────────
export interface TrajectoryPoint {
  x: number;
  y: number;
  t: number;
  /** Geographic latitude — computed from x,y at import time via enuToLatLng() */
  lat: number;
  /** Geographic longitude — computed from x,y at import time via enuToLatLng() */
  lon: number;
  // Present only on fused_output / smoothed_output points (real EKF data, see
  // backend/export_frontend_data.py):
  status?: 'healthy' | 'degraded' | 'outage' | 'unavailable';
  uncertainty?: number;
  velocity?: number;
  heading?: number;
}

// ── Augment raw JSON with lat/lon once at module load time (not per-render) ──
// Each JSON has ~4600 points; this runs once and the result is cached in the
// module. Subsequent hook calls just reference these arrays — zero allocation.
function augment(raw: object[]): TrajectoryPoint[] {
  return (raw as Array<{ x: number; y: number; t: number; [k: string]: unknown }>).map(p => ({
    ...p,
    ...enuToLatLng(p.x, p.y),
  } as TrajectoryPoint));
}

const GT       = augment(groundTruthData   as object[]);
const GNSS     = augment(gnssOnlyData      as object[]);
const FUSED    = augment(fusedOutputData   as object[]);
const SMOOTHED = augment(smoothedOutputData as object[]);

// ── Hook ─────────────────────────────────────────────────────────────────────
export const useTrajectoryData = () => {
  const { progress } = useDashboardContext();

  // All four arrays are the SAME length and time-aligned by
  // export_frontend_data.py (aligned to fused_output's time grid).
  const currentIndex = Math.max(0, Math.floor(GT.length * progress) - 1);

  return {
    gt: GT,
    gnss: GNSS,
    fused: FUSED,
    smoothed: SMOOTHED,
    currentIndex,
    currentGnssPos:      GNSS[currentIndex],
    currentFusedPos:     FUSED[currentIndex],
    currentSmoothedPos:  SMOOTHED[currentIndex],
  };
};
