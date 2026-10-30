package com.aeris.mobile.util

import java.util.Locale
import kotlin.math.roundToInt

object Formatters {
    private val ROSE = listOf("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")

    /**
     * Converts heading in degrees (0..360) to a 16-point compass rose cardinal direction.
     * Guaranteed to correctly map boundary angles and negatives/wraparounds.
     */
    fun cardinal16(deg: Double): String {
        val d = ((deg % 360.0) + 360.0) % 360.0
        return ROSE[(((d + 11.25) / 22.5).toInt()) % 16]
    }

    /**
     * Formats uncertainty or meter values per R6 § 3.3:
     * - null -> "—"
     * - < 1.0 m -> "<1 m"
     * - < 10.0 m -> "%.1f m"
     * - >= 10.0 m -> integer rounded "X m"
     */
    fun formatMeters(m: Double?): String = when {
        m == null -> "—"
        m < 1.0   -> "<1 m"
        m < 10.0  -> String.format(Locale.getDefault(), "%.1f m", m)
        else      -> "${m.roundToInt()} m"
    }

    /**
     * Formats distance in meters or kilometers.
     * e.g. "300 m", "1.4 km", "3.4 km".
     */
    fun formatDistance(meters: Double?): String = when {
        meters == null -> "—"
        meters < 1000.0 -> "${meters.roundToInt()} m"
        else -> String.format(Locale.getDefault(), "%.1f km", meters / 1000.0)
    }

    /**
     * Formats elapsed or duration time in mm:ss format.
     */
    fun formatMmSs(seconds: Double?): String {
        if (seconds == null) return "00:00"
        val s = seconds.toInt().coerceAtLeast(0)
        return String.format(Locale.getDefault(), "%02d:%02d", s / 60, s % 60)
    }

    /**
     * Formats speed in km/h or m/s.
     */
    fun formatSpeedKmh(speedMps: Double?): String {
        if (speedMps == null) return "—"
        val kmh = (speedMps * 3.6).roundToInt()
        return "$kmh km/h"
    }
}
