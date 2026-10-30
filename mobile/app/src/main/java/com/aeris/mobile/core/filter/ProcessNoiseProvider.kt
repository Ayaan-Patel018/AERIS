package com.aeris.mobile.core.filter

/**
 * Provides the process-noise covariance matrix Q for the 15-state ES-EKF,
 * parameterised by the current [MotionMode].
 *
 * ## Design rationale
 * Rather than baking a single hardcoded Q into the filter, the noise
 * parameters are selected per motion mode. This means the filter can be
 * tighter when the vehicle is stopped (low Q) and looser during dynamic
 * manoeuvres (high Q), without rewriting the filter core.
 *
 * When a full IMM (Interacting Multiple Model) filter is added later,
 * each model bank can instantiate its own [ProcessNoiseProvider] with
 * different parameter sets and the filter's predict step stays unchanged.
 */
interface ProcessNoiseProvider {
    /**
     * Returns the discrete-time 15×15 process-noise covariance matrix Q_d
     * for the given mode and time step.
     *
     * @param mode The current motion classification.
     * @param dt   Time step in seconds since the last prediction.
     */
    fun getProcessNoise(mode: MotionMode, dt: Double): Matrix
}

/**
 * Default [ProcessNoiseProvider] with tunable per-mode noise spectral
 * densities.
 *
 * The noise model assumes:
 * - Accelerometer white noise drives velocity uncertainty.
 * - Gyroscope white noise drives attitude uncertainty.
 * - Accelerometer and gyroscope biases follow random walks.
 *
 * All parameters are continuous-time power spectral densities (PSD),
 * discretised as Q_d ≈ Q_c · dt.
 */
class DefaultProcessNoiseProvider(
    /**
     * Per-mode noise parameters.
     * If a mode is missing the [defaultParams] are used.
     */
    private val modeParams: Map<MotionMode, NoiseParams> = defaultModeParams(),
    private val defaultParams: NoiseParams = NoiseParams(),
) : ProcessNoiseProvider {

    /**
     * Continuous-time noise spectral density parameters.
     *
     * @property accelNoisePsd  Accelerometer noise PSD (m/s²)²/Hz — drives δv.
     * @property gyroNoisePsd   Gyroscope noise PSD (rad/s)²/Hz — drives δθ.
     * @property accelBiasWalk  Accel bias random walk PSD (m/s²)²·s — drives δbₐ.
     * @property gyroBiasWalk   Gyro bias random walk PSD (rad/s)²·s — drives δbg.
     * @property positionPsd    Position process noise PSD (m²/s) — small,
     *                          accounts for model mismatch in position.
     */
    data class NoiseParams(
        val accelNoisePsd: Double = 0.04,       // σ_a ≈ 0.2 m/s²
        val gyroNoisePsd: Double = 1e-4,        // σ_g ≈ 0.01 rad/s
        val accelBiasWalk: Double = 1e-5,       // slow bias drift
        val gyroBiasWalk: Double = 1e-7,        // slow bias drift
        val positionPsd: Double = 0.001,        // minimal position noise
    )

    override fun getProcessNoise(mode: MotionMode, dt: Double): Matrix {
        val p = modeParams[mode] ?: defaultParams
        val q = Matrix(EsEkfState.STATE_DIM, EsEkfState.STATE_DIM)

        // Position noise
        for (i in 0..2) q[i, i] = p.positionPsd * dt
        // Velocity noise (accelerometer-driven)
        for (i in 3..5) q[i, i] = p.accelNoisePsd * dt
        // Attitude noise (gyroscope-driven)
        for (i in 6..8) q[i, i] = p.gyroNoisePsd * dt
        // Accel bias random walk
        for (i in 9..11) q[i, i] = p.accelBiasWalk * dt
        // Gyro bias random walk
        for (i in 12..14) q[i, i] = p.gyroBiasWalk * dt

        return q
    }

    companion object {
        /**
         * Default per-mode noise parameter map.
         *
         * - **STOPPED**: very low noise — ZUPT/ZARU will also constrain.
         * - **CRUISING**: moderate noise — steady motion.
         * - **TURNING**: elevated gyro noise to accommodate turn dynamics.
         * - **BRAKING**: elevated accel noise to accommodate deceleration.
         */
        fun defaultModeParams(): Map<MotionMode, NoiseParams> = mapOf(
            MotionMode.STOPPED to NoiseParams(
                accelNoisePsd = 0.01,
                gyroNoisePsd = 1e-5,
                accelBiasWalk = 1e-6,
                gyroBiasWalk = 1e-8,
                positionPsd = 1e-4,
            ),
            MotionMode.CRUISING to NoiseParams(
                accelNoisePsd = 0.04,
                gyroNoisePsd = 1e-4,
                accelBiasWalk = 1e-5,
                gyroBiasWalk = 1e-7,
                positionPsd = 0.001,
            ),
            MotionMode.TURNING to NoiseParams(
                accelNoisePsd = 0.1,
                gyroNoisePsd = 5e-4,
                accelBiasWalk = 1e-5,
                gyroBiasWalk = 1e-6,
                positionPsd = 0.005,
            ),
            MotionMode.BRAKING to NoiseParams(
                accelNoisePsd = 0.2,
                gyroNoisePsd = 1e-4,
                accelBiasWalk = 5e-5,
                gyroBiasWalk = 1e-7,
                positionPsd = 0.005,
            ),
        )
    }
}
