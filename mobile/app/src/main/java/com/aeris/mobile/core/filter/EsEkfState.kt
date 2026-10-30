package com.aeris.mobile.core.filter

/**
 * Nominal and error-state representation for the 15-state ES-EKF.
 *
 * ## State vector layout (error-state δx, 15 × 1):
 * | Index  | Symbol | Description                          |
 * |--------|--------|--------------------------------------|
 * | 0–2    | δp     | Position error (NED, metres)         |
 * | 3–5    | δv     | Velocity error (NED, m/s)            |
 * | 6–8    | δθ     | Attitude error (rotation vector, rad)|
 * | 9–11   | δbₐ    | Accelerometer bias error (m/s²)      |
 * | 12–14  | δbg    | Gyroscope bias error (rad/s)         |
 *
 * The **nominal state** is propagated by the full non-linear INS
 * mechanization equations.  The **error state** captures the linearised
 * perturbation; after each measurement update the error is injected back
 * into the nominal state and reset to zero.
 */
data class EsEkfState(
    // ── Nominal state ───────────────────────────────────────────────────

    /** Position in local NED frame relative to the origin (metres). */
    val positionNed: DoubleArray = DoubleArray(3),

    /** Velocity in the NED frame (m/s). */
    val velocityNed: DoubleArray = DoubleArray(3),

    /** Attitude quaternion (body → NED). Scalar-first [w, x, y, z]. */
    val attitude: Quaternion = Quaternion.identity(),

    /** Accelerometer bias estimate in body frame (m/s²). */
    val accelBias: DoubleArray = DoubleArray(3),

    /** Gyroscope bias estimate in body frame (rad/s). */
    val gyroBias: DoubleArray = DoubleArray(3),

    // ── Origin reference (set once on first GNSS fix) ───────────────────

    /** WGS-84 latitude of the local NED origin (radians). */
    val originLat: Double = 0.0,

    /** WGS-84 longitude of the local NED origin (radians). */
    val originLon: Double = 0.0,

    /** WGS-84 altitude (metres above ellipsoid) of the NED origin. */
    val originAlt: Double = 0.0,

    /** Whether the NED origin has been initialised by a GNSS fix. */
    val originInitialised: Boolean = false,

    // ── Error-state covariance ──────────────────────────────────────────

    /** 15 × 15 error-state covariance matrix P. */
    val covariance: Matrix = defaultCovariance(),

    // ── Bookkeeping ─────────────────────────────────────────────────────

    /** Timestamp of the last prediction step (sensor event nanos). */
    val lastPredictTimestampNanos: Long = 0L,

    /** Timestamp of the last GNSS update (system millis). */
    val lastGnssTimestampMillis: Long = 0L,
) {

    /** Total number of error states. */
    companion object {
        const val STATE_DIM = 15

        /** WGS-84 semi-major axis (metres). */
        const val WGS84_A = 6_378_137.0

        /** WGS-84 flattening. */
        const val WGS84_F = 1.0 / 298.257223563

        /** Approximate gravitational acceleration (m/s²). */
        const val GRAVITY = 9.80665

        /**
         * Returns the default initial covariance. Large initial uncertainty
         * for position/velocity/attitude, small for biases.
         */
        fun defaultCovariance(): Matrix {
            val p = Matrix.identity(STATE_DIM)
            // Position: σ = 10 m  → P = 100
            for (i in 0..2) p[i, i] = 100.0
            // Velocity: σ = 1 m/s → P = 1
            for (i in 3..5) p[i, i] = 1.0
            // Attitude: σ = 5° ≈ 0.087 rad → P = 0.0076
            for (i in 6..8) p[i, i] = 0.0076
            // Accel bias: σ = 0.1 m/s² → P = 0.01
            for (i in 9..11) p[i, i] = 0.01
            // Gyro bias: σ = 0.01 rad/s → P = 0.0001
            for (i in 12..14) p[i, i] = 0.0001
            return p
        }
    }

    // -- Coordinate conversions --

    /**
     * Converts WGS-84 geodetic coordinates to local NED position relative
     * to the stored origin using a flat-earth approximation.
     *
     * Accuracy is better than 1 m for distances up to ~10 km, which
     * exceeds the useful range of dead reckoning.
     */
    fun geodeticToNed(latRad: Double, lonRad: Double, altM: Double): DoubleArray {
        val dLat = latRad - originLat
        val dLon = lonRad - originLon
        val rN = WGS84_A // simplified — ignores flattening
        val rE = WGS84_A * kotlin.math.cos(originLat)

        return doubleArrayOf(
            dLat * rN,        // North
            dLon * rE,        // East
            -(altM - originAlt) // Down (NED convention: positive downward)
        )
    }

    /**
     * Converts local NED position back to WGS-84 geodetic coordinates.
     */
    fun nedToGeodetic(ned: DoubleArray): Triple<Double, Double, Double> {
        val rN = WGS84_A
        val rE = WGS84_A * kotlin.math.cos(originLat)

        val lat = originLat + ned[0] / rN
        val lon = originLon + ned[1] / rE
        val alt = originAlt - ned[2]
        return Triple(lat, lon, alt)
    }

    // ── equals/hashCode for DoubleArray fields ──────────────────────────

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is EsEkfState) return false
        return positionNed.contentEquals(other.positionNed) &&
                velocityNed.contentEquals(other.velocityNed) &&
                attitude == other.attitude &&
                accelBias.contentEquals(other.accelBias) &&
                gyroBias.contentEquals(other.gyroBias)
    }

    override fun hashCode(): Int {
        var result = positionNed.contentHashCode()
        result = 31 * result + velocityNed.contentHashCode()
        result = 31 * result + attitude.hashCode()
        return result
    }
}
