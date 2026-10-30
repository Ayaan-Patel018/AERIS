package com.aeris.mobile.service

import com.aeris.mobile.core.filter.MotionMode

/**
 * A single point on the tracked route, stored for rendering the route
 * polyline and the trip-summary timeline.
 *
 * @property lat WGS-84 latitude (degrees).
 * @property lon WGS-84 longitude (degrees).
 * @property confidence The filter's 0–100 confidence score at this point.
 * @property isGnssLocked Whether GNSS was available when this point was emitted.
 * @property timestampMillis Wall-clock time (UTC millis).
 */
data class RoutePoint(
    val lat: Double,
    val lon: Double,
    val confidence: Int,
    val isGnssLocked: Boolean,
    val timestampMillis: Long,
)

/**
 * Health status for a single sensor subsystem.
 */
enum class SensorStatus {
    /** Sensor is active and producing data. */
    ACTIVE,
    /** Sensor is producing data but quality is degraded. */
    DEGRADED,
    /** Sensor is unavailable or not producing data. */
    UNAVAILABLE,
}

/**
 * Aggregate sensor health across GNSS, IMU, and barometer.
 */
data class SensorHealth(
    val gnss: SensorStatus = SensorStatus.UNAVAILABLE,
    val imu: SensorStatus = SensorStatus.UNAVAILABLE,
    val baro: SensorStatus = SensorStatus.UNAVAILABLE,
)

/**
 * Complete tracking state exposed by the foreground service to the UI
 * via [kotlinx.coroutines.flow.StateFlow].
 *
 * Every field here drives a real UI element — no hardcoded demo values.
 */
data class TrackingState(
    /** Current latitude (degrees, WGS-84). */
    val latitude: Double = 0.0,
    /** Current longitude (degrees, WGS-84). */
    val longitude: Double = 0.0,
    /** Current altitude (metres above ellipsoid). */
    val altitude: Double = 0.0,
    /** Position confidence score, 0–100. */
    val confidence: Int = 100,
    /** Whether a recent GNSS fix is available. */
    val isGnssAvailable: Boolean = false,
    /** Seconds since GNSS was last available, or 0 if available now. */
    val gnssLostDurationSec: Long = 0,
    /** Current motion mode classification. */
    val motionMode: MotionMode = MotionMode.STOPPED,
    /** Recorded route for polyline rendering. */
    val routePoints: List<RoutePoint> = emptyList(),
    /** Cumulative distance travelled (metres). */
    val distanceTraveledMeters: Double = 0.0,
    /** Whether the service is actively tracking. */
    val isTracking: Boolean = false,
    /** Per-sensor health indicators. */
    val sensorHealth: SensorHealth = SensorHealth(),
    /**
     * Placeholder mode probabilities for future IMM.
     * Currently the active mode gets 1.0, others get 0.0.
     */
    val modeProbabilities: Map<MotionMode, Float> = MotionMode.entries
        .associateWith { 0f },
    /** Maximum position uncertainty (σ in metres) seen during this trip. */
    val maxDriftMeters: Double = 0.0,
    /** Running average confidence across the trip. */
    val averageConfidence: Double = 100.0,
    /** Cumulative time without GNSS during this trip (seconds). */
    val totalGnssOutageSec: Long = 0,
    /** Latest accelerometer reading [ax, ay, az] */
    val currentAccel: List<Double> = listOf(0.0, 0.0, 0.0),
    /** Latest gyroscope reading [wx, wy, wz] */
    val currentGyro: List<Double> = listOf(0.0, 0.0, 0.0),
    /** GPS ground speed in km/h (0 when unavailable). */
    val currentSpeedKmh: Float = 0f,
    /** GPS bearing in degrees (0 = north, clockwise). 0 when unavailable. */
    val currentBearing: Float = 0f,
)
