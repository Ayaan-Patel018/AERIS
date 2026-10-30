package com.aeris.mobile.domain.model

/**
 * GNSS health status as exported by AERIS pipeline.
 */
enum class GnssStatus {
    HEALTHY,
    OUTAGE,
    DEGRADED,
    UNKNOWN;

    companion object {
        fun fromString(str: String?): GnssStatus {
            return when (str?.lowercase()?.trim()) {
                "healthy" -> HEALTHY
                "outage", "unavailable" -> OUTAGE
                "degraded" -> DEGRADED
                else -> UNKNOWN
            }
        }
    }
}

/**
 * A single timestamped state frame in a drive trajectory.
 */
data class TrajectoryPoint(
    val lat: Double,
    val lon: Double,
    val headingDeg: Double?,
    val speedMps: Double?,
    val timestampSec: Double,
    val status: GnssStatus,
    val sigma: Double?,
    val covXX: Double?,
    val covYY: Double?,
    val covXY: Double?,
    val distanceMeters: Double = 0.0,
    // aeris-trip/1 frame fields (null for points that do not come from an export)
    val sigmaMajorM: Double? = null,      // 1-sigma ellipse semi-major axis, m
    val sigmaMinorM: Double? = null,      // 1-sigma ellipse semi-minor axis, m
    val ellipseAngleDeg: Double? = null,  // major axis, degrees clockwise from North, [0, 180)
    val fixAgeS: Double? = null,          // seconds since the last usable phone fix
    val stationary: Boolean? = null,      // filter's IMU standstill flag
)

/**
 * Dynamically detected GNSS denial window.
 * Derived from state transitions in the data, never hardcoded.
 */
data class OutageWindow(
    val id: String,
    val startIndex: Int,
    val endIndex: Int,
    val startSec: Double,
    val endSec: Double,
    val durationSec: Double,
    val startPoint: TrajectoryPoint,
    val endPoint: TrajectoryPoint,
    val maxUncertaintyMeters: Double,
    // aeris-trip/1 outages[] fields
    val kind: String? = null,             // "simulated": the phone had fixes, the export withheld them
    val lastFixSec: Double? = null,       // last phone fix before startSec
    val firstFixAfterSec: Double? = null, // first phone fix after endSec
    val withheldFixCount: Int? = null,
)

/**
 * A displayed position step > 5 m between consecutive frames (aeris-trip/1 corrections[]).
 * Drawn dashed, never as driving. [frameIndex] is the frame the step lands on.
 */
data class Correction(
    val tSec: Double,
    val frameIndex: Int,
    val fromLat: Double,
    val fromLon: Double,
    val toLat: Double,
    val toLon: Double,
    val jumpM: Double,
    val cause: String,
)

/**
 * Performance and evaluation metrics with provenance from metrics.json / evaluation run.
 */
data class DriveMetrics(
    val maxDriftMeters: Double,
    val meanErrorMeters: Double,
    val cep50Meters: Double? = null,
    val r95Meters: Double? = null,
    val totalOutageDurationSec: Double,
    val provenance: String = "metrics.json",
    val endErrorMeters: Double? = null,
    val pathRatio: Double? = null,
    val insideOneSigmaPct: Double? = null,
    val inSample: Boolean? = null,
)

/**
 * Summary metadata for an individual drive.
 */
data class DriveMeta(
    val id: String,
    val name: String,
    val durationSec: Double,
    val totalDistanceMeters: Double,
    val outageCount: Int,
    val dateString: String? = null,
    val referenceAvailable: Boolean = false,
    val metricsAvailable: Boolean = false,
    // aeris-trip/1 meta fields
    val filter: String? = null,
    val note: String? = null,
    val schema: String? = null,
    val schemaStatus: String? = null,
    val gitCommit: String? = null,
    val sigmaCalibrated: Boolean? = null,
)

/**
 * Complete Drive container holding full trajectory, outages, baseline, and metadata.
 */
data class Drive(
    val meta: DriveMeta,
    val points: List<TrajectoryPoint>,
    val outages: List<OutageWindow>,
    val baselinePoints: List<TrajectoryPoint> = emptyList(),
    val referencePoints: List<TrajectoryPoint> = emptyList(),
    val metrics: DriveMetrics? = null,
    val corrections: List<Correction> = emptyList(),
)
