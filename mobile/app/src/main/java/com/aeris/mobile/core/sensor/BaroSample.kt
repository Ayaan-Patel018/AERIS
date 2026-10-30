package com.aeris.mobile.core.sensor

/**
 * Timestamped barometric pressure / altitude reading.
 *
 * @property pressureHpa  Raw pressure in hectopascals (hPa / mbar).
 * @property altitudeMetres Approximate altitude derived from pressure via
 *                          [android.hardware.SensorManager.getAltitude].
 * @property timestampNanos Monotonic event timestamp (nanoseconds since boot).
 */
data class BaroSample(
    val pressureHpa: Float,
    val altitudeMetres: Float,
    val timestampNanos: Long,
)
