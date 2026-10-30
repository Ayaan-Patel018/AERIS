package com.aeris.mobile.core.filter

import kotlin.math.sqrt

/**
 * Zero-velocity update (ZUPT) and zero-angular-rate update (ZARU) detector.
 *
 * Uses a simple sliding-window variance test on accelerometer and gyroscope
 * magnitude to determine if the device is stationary. When stationary:
 * - ZUPT constrains velocity to zero.
 * - ZARU constrains angular rate to zero, helping estimate gyro bias.
 *
 * ## Tunable thresholds
 * All thresholds are public constants — adjust them per deployment
 * environment without modifying the detection logic.
 */
object ZuptDetector {

    // ── Thresholds ──────────────────────────────────────────────────────

    /**
     * Accel-magnitude variance threshold (m/s²)².
     * If the windowed variance of ‖a‖ falls below this, the device is
     * considered stationary for ZUPT purposes.
     */
    const val ACCEL_VARIANCE_THRESHOLD = 0.5

    /**
     * Gyro-magnitude variance threshold (rad/s)².
     * If the windowed variance of ‖ω‖ falls below this, the device is
     * considered rotationally stationary for ZARU purposes.
     */
    const val GYRO_VARIANCE_THRESHOLD = 0.05

    /**
     * Minimum number of samples in the sliding window before a
     * detection decision is made. Avoids false triggers on startup.
     */
    const val WINDOW_SIZE = 50

    // ── Detection logic ─────────────────────────────────────────────────

    /**
     * Computes the sample variance of a list of scalar values.
     *
     * @param values At least 2 values; returns 0 if fewer.
     * @return Population variance (not Bessel-corrected — we only need
     *         a rough magnitude for thresholding).
     */
    fun variance(values: List<Double>): Double {
        if (values.size < 2) return 0.0
        val mean = values.average()
        return values.sumOf { (it - mean) * (it - mean) } / values.size
    }

    /**
     * Computes the Euclidean norm of a 3-vector.
     */
    fun norm3(v: DoubleArray): Double {
        require(v.size >= 3) { "Need at least 3 elements" }
        return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    }

    /**
     * Returns `true` if the recent accelerometer magnitudes indicate
     * the device is stationary (suitable for a ZUPT).
     *
     * @param accelMagnitudes Rolling window of ‖a‖ values. Must have at
     *                        least [WINDOW_SIZE] entries for a reliable
     *                        decision; returns `false` otherwise.
     */
    fun isStationary(accelMagnitudes: List<Double>): Boolean {
        if (accelMagnitudes.size < WINDOW_SIZE) return false
        val recent = accelMagnitudes.takeLast(WINDOW_SIZE)
        return variance(recent) < ACCEL_VARIANCE_THRESHOLD
    }

    /**
     * Returns `true` if the recent gyroscope magnitudes indicate
     * zero angular rate (suitable for a ZARU).
     *
     * @param gyroMagnitudes Rolling window of ‖ω‖ values. Must have at
     *                       least [WINDOW_SIZE] entries.
     */
    fun isZeroAngularRate(gyroMagnitudes: List<Double>): Boolean {
        if (gyroMagnitudes.size < WINDOW_SIZE) return false
        val recent = gyroMagnitudes.takeLast(WINDOW_SIZE)
        return variance(recent) < GYRO_VARIANCE_THRESHOLD
    }
}
