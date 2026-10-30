package com.aeris.mobile.domain.math

import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Geometric parameter representation of an uncertainty ellipse.
 */
data class UncertaintyEllipse(
    val semiMajorMeters: Double,
    val semiMinorMeters: Double,
    val orientationRad: Double,
    val centerLat: Double,
    val centerLon: Double,
)

/**
 * Mathematical calculations for 2-DoF horizontal uncertainty ellipses
 * derived from the filter covariance matrix [covXX, covYY, covXY].
 */
object EllipseMath {

    // 2-DoF Chi-square scale factors
    const val SCALE_1_SIGMA = 1.0
    // sqrt(5.991) for 95% confidence 2-DoF ellipse
    const val SCALE_95_PERCENT = 2.4477467

    private const val METERS_PER_DEGREE_LAT = 111139.0

    /**
     * Computes the semi-major, semi-minor, and orientation angle of the uncertainty ellipse
     * from horizontal covariance components (in m^2).
     */
    fun computeEllipse(
        centerLat: Double,
        centerLon: Double,
        covXX: Double,
        covYY: Double,
        covXY: Double,
        use95Percent: Boolean = false,
    ): UncertaintyEllipse {
        val trace = covXX + covYY
        val det = (covXX * covYY) - (covXY * covXY)
        val term = sqrt(((trace / 2.0) * (trace / 2.0) - det).coerceAtLeast(0.0))

        val lambda1 = (trace / 2.0 + term).coerceAtLeast(0.0)
        val lambda2 = (trace / 2.0 - term).coerceAtLeast(0.0)

        val scale = if (use95Percent) SCALE_95_PERCENT else SCALE_1_SIGMA

        val semiMajor = sqrt(lambda1) * scale
        val semiMinor = sqrt(lambda2) * scale

        // Angle in radians between the major axis and East
        val orientation = 0.5 * atan2(2.0 * covXY, covXX - covYY)

        return UncertaintyEllipse(
            semiMajorMeters = semiMajor.coerceAtLeast(0.5),
            semiMinorMeters = semiMinor.coerceAtLeast(0.5),
            orientationRad = orientation,
            centerLat = centerLat,
            centerLon = centerLon,
        )
    }

    /**
     * Generates a closed polygon ring of (lat, lon) coordinates representing the ellipse boundary.
     * Suitable for Mapbox GeoJSON Polygon or Canvas drawing.
     */
    fun generatePolygonPoints(
        ellipse: UncertaintyEllipse,
        steps: Int = 36,
    ): List<Pair<Double, Double>> {
        val points = mutableListOf<Pair<Double, Double>>()
        val latRad = Math.toRadians(ellipse.centerLat)
        val metersPerDegreeLon = METERS_PER_DEGREE_LAT * cos(latRad).coerceAtLeast(0.01)

        val cosTheta = cos(ellipse.orientationRad)
        val sinTheta = sin(ellipse.orientationRad)

        for (i in 0..steps) {
            val angle = 2.0 * PI * i / steps
            val xLocal = ellipse.semiMajorMeters * cos(angle)
            val yLocal = ellipse.semiMinorMeters * sin(angle)

            // Rotate into East-North coordinates
            val eastMeters = xLocal * cosTheta - yLocal * sinTheta
            val northMeters = xLocal * sinTheta + yLocal * cosTheta

            val pointLat = ellipse.centerLat + (northMeters / METERS_PER_DEGREE_LAT)
            val pointLon = ellipse.centerLon + (eastMeters / metersPerDegreeLon)

            points.add(Pair(pointLat, pointLon))
        }

        return points
    }
}
