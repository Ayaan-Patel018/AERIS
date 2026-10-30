package com.aeris.mobile.core.filter

/**
 * Discrete motion modes used to select process-noise parameters.
 *
 * The EKF's process noise Q is not a single hardcoded matrix — the
 * [ProcessNoiseProvider] returns a mode-specific Q so that the filter can
 * be tuned per-mode without rewriting the filter core. This enum is also
 * surfaced in the UI's bottom sheet as probability bars.
 *
 * A simple classifier ([MotionModeClassifier]) maps recent IMU statistics
 * to one of these modes. Full IMM (Interacting Multiple Model) filtering
 * can be added later by running parallel filters per mode and blending.
 */
enum class MotionMode {
    /** Device is stationary (ZUPT/ZARU applicable). */
    STOPPED,

    /** Steady forward motion with low lateral acceleration. */
    CRUISING,

    /** Significant yaw-rate detected (turning manoeuvre). */
    TURNING,

    /** Significant longitudinal deceleration detected. */
    BRAKING,
}

/**
 * Classifies the current motion mode from recent IMU statistics.
 *
 * This is a simple threshold-based classifier. The thresholds are
 * exposed as tunable constants so they can be adjusted without modifying
 * the classifier logic.
 */
object MotionModeClassifier {

    /** Accel magnitude variance threshold below which the device is stopped (m/s²)². */
    const val STOPPED_ACCEL_VAR = 0.5

    /** Gyro magnitude variance threshold below which the device is stopped (rad/s)². */
    const val STOPPED_GYRO_VAR = 0.05

    /** Yaw-rate threshold above which the device is turning (rad/s). */
    const val TURNING_GYRO_THRESHOLD = 0.15

    /** Forward deceleration threshold for braking detection (m/s²). */
    const val BRAKING_DECEL_THRESHOLD = -1.5

    /**
     * Determines the current [MotionMode] from IMU statistics.
     *
     * @param accelVariance  Variance of ‖accelerometer‖ over recent window.
     * @param gyroVariance   Variance of ‖gyroscope‖ over recent window.
     * @param yawRate        Current yaw rate magnitude (rad/s).
     * @param forwardAccel   Longitudinal acceleration in body frame (m/s²).
     */
    fun classify(
        accelVariance: Double,
        gyroVariance: Double,
        yawRate: Double,
        forwardAccel: Double,
    ): MotionMode = when {
        accelVariance < STOPPED_ACCEL_VAR && gyroVariance < STOPPED_GYRO_VAR -> MotionMode.STOPPED
        yawRate > TURNING_GYRO_THRESHOLD -> MotionMode.TURNING
        forwardAccel < BRAKING_DECEL_THRESHOLD -> MotionMode.BRAKING
        else -> MotionMode.CRUISING
    }
}
