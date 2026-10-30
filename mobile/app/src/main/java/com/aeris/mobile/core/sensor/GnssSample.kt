package com.aeris.mobile.core.sensor

/**
 * Timestamped GNSS position fix from the Fused Location Provider.
 *
 * @property latitude  WGS-84 latitude (degrees).
 * @property longitude WGS-84 longitude (degrees).
 * @property altitude  Altitude above the WGS-84 ellipsoid (metres).
 * @property accuracy  Estimated horizontal accuracy radius (metres, 68th %).
 * @property speed     Ground speed (m/s), or 0 if unavailable.
 * @property bearing   Bearing in degrees (0 = north, clockwise), or 0.
 * @property timestampMillis UTC wall-clock time from [android.location.Location.getTime].
 */
data class GnssSample(
    val latitude: Double,
    val longitude: Double,
    val altitude: Double,
    val accuracy: Float,
    val speed: Float,
    val bearing: Float,
    val timestampMillis: Long,
)
