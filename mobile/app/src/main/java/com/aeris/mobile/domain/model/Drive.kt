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
)
