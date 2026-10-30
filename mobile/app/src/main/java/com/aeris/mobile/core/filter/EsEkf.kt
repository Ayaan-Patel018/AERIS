package com.aeris.mobile.core.filter

import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * 15-state Error-State Extended Kalman Filter for inertial navigation.
 *
 * ## Algorithm overview
 * The filter maintains a **nominal state** (position, velocity, attitude,
 * IMU biases) propagated by the full non-linear INS equations, and a
 * **linearised error state** δx (15-dim) with covariance P (15×15).
 *
 * 1. **Predict** — each IMU sample drives the nominal state forward via
 *    strap-down integration and propagates P through the linearised
 *    error-state transition Φ.
 * 2. **Update** — GNSS, ZUPT, ZARU, NHC, or baro observations correct
 *    the error state δx; the correction is *injected* into the nominal
 *    state and δx is reset to zero.
 *
 * ## Thread safety
 * Not thread-safe — the [TrackingService] must serialise calls on its
 * coroutine dispatcher.
 *
 * ## References
 * - Solà, *Quaternion kinematics for the error-state Kalman filter*, 2017
 * - Groves, *Principles of GNSS, Inertial, and Multisensor Integrated
 *   Navigation Systems*, 2nd ed.
 *
 * @param processNoiseProvider Supplies Q per motion mode — swap this out
 *                             when adding IMM without touching filter code.
 */
class EsEkf(
    private val processNoiseProvider: ProcessNoiseProvider = DefaultProcessNoiseProvider()
) {

    /** Current filter state (nominal + covariance). */
    var state: EsEkfState = EsEkfState()

    /** Timestamp (nanos) of the most recent GNSS fix, or 0 if none. */
    var lastGnssNanos: Long = 0L
        private set

    /** Innovation norm from the most recent GNSS update (m). */
    var lastGnssInnovationNorm: Double = 0.0
        private set

    /** Current motion mode (for Q selection and UI display). */
    var currentMotionMode: MotionMode = MotionMode.STOPPED
        private set

    // ── Predict ─────────────────────────────────────────────────────────

    /**
     * INS mechanisation + error-state covariance propagation.
     *
     * Call this once per IMU sample (~100 Hz). The function:
     * 1. Compensates IMU measurements for estimated biases.
     * 2. Updates the nominal attitude, velocity, and position.
     * 3. Constructs the linearised error-state transition Φ.
     * 4. Propagates covariance: P = Φ P Φᵀ + Q_d.
     *
     * @param accel Raw accelerometer reading [ax, ay, az] in body frame (m/s²).
     * @param gyro  Raw gyroscope reading [ωx, ωy, ωz] in body frame (rad/s).
     * @param dt    Time step in seconds since the previous predict call.
     * @param motionMode Current motion classification (drives Q selection).
     */
    fun predict(
        accel: DoubleArray,
        gyro: DoubleArray,
        dt: Double,
        motionMode: MotionMode = MotionMode.CRUISING,
    ) {
        if (dt <= 0.0 || dt > 1.0) return // guard against bad timestamps
        currentMotionMode = motionMode
        val s = state

        // 1. Bias-compensated measurements
        val fBody = doubleArrayOf(
            accel[0] - s.accelBias[0],
            accel[1] - s.accelBias[1],
            accel[2] - s.accelBias[2],
        )
        val wBody = doubleArrayOf(
            gyro[0] - s.gyroBias[0],
            gyro[1] - s.gyroBias[1],
            gyro[2] - s.gyroBias[2],
        )

        // 2. Rotation matrix body → NED
        val cBn = s.attitude.toRotationMatrix()

        // 3. Specific force in NED
        val fNed = cBn.multiplyVector(fBody)

        // 4. Gravity in NED (positive down)
        val gNed = doubleArrayOf(0.0, 0.0, EsEkfState.GRAVITY)

        // 5. Velocity update:  v += (C·f + g) · dt
        val newVel = doubleArrayOf(
            s.velocityNed[0] + (fNed[0] + gNed[0]) * dt,
            s.velocityNed[1] + (fNed[1] + gNed[1]) * dt,
            s.velocityNed[2] + (fNed[2] + gNed[2]) * dt,
        )

        // 6. Position update:  p += v · dt  (first-order at high rate)
        val newPos = doubleArrayOf(
            s.positionNed[0] + s.velocityNed[0] * dt,
            s.positionNed[1] + s.velocityNed[1] * dt,
            s.positionNed[2] + s.velocityNed[2] * dt,
        )

        // 7. Attitude update:  q = q ⊗ Δq(ω·dt)
        val dq = Quaternion.fromAngularVelocity(wBody, dt)
        val newAtt = (s.attitude * dq).normalize()

        // ── Error-state propagation ─────────────────────────────────────

        // Build F (15×15 continuous-time Jacobian), then Φ ≈ I + F·dt
        val phi = Matrix.identity(EsEkfState.STATE_DIM)

        // F[0:3, 3:6] = I₃  →  Φ[0:3, 3:6] = I₃ · dt
        for (i in 0..2) phi[i, 3 + i] = dt

        // F[3:6, 6:9] = -C·[f_b]×  (velocity ↔ attitude coupling)
        // Specific force in NED, then skew-symmetric
        val fNedSkew = Matrix.skewSymmetric(fNed)
        val negFnSkew = fNedSkew * (-1.0)
        for (i in 0..2) for (j in 0..2) phi[3 + i, 6 + j] = negFnSkew[i, j] * dt

        // F[3:6, 9:12] = -C_bn  (velocity ↔ accel bias)
        val negCbn = cBn * (-1.0)
        for (i in 0..2) for (j in 0..2) phi[3 + i, 9 + j] = negCbn[i, j] * dt

        // F[6:9, 6:9] = -[ω_b]×  (attitude ↔ attitude)
        val wSkew = Matrix.skewSymmetric(wBody)
        val negWSkew = wSkew * (-1.0)
        for (i in 0..2) for (j in 0..2) phi[6 + i, 6 + j] += negWSkew[i, j] * dt

        // F[6:9, 12:15] = -I₃  (attitude ↔ gyro bias)
        for (i in 0..2) phi[6 + i, 12 + i] = -dt

        // Covariance propagation:  P = Φ P Φᵀ + Q_d
        val phiT = phi.transpose()
        val qd = processNoiseProvider.getProcessNoise(motionMode, dt)
        val newCov = phi * s.covariance * phiT + qd

        state = s.copy(
            positionNed = newPos,
            velocityNed = newVel,
            attitude = newAtt,
            covariance = newCov,
        )
    }

    // ── GNSS measurement update ─────────────────────────────────────────

    /**
     * Applies a GNSS position fix as a measurement update.
     *
     * The observation model is:
     *   z = p_gnss − p_nominal  (in NED metres)
     *   H = [I₃  0  0  0  0]   (3×15)
     *   R = diag(σ²)            (from GNSS accuracy)
     *
     * @param latRad  WGS-84 latitude in radians.
     * @param lonRad  WGS-84 longitude in radians.
     * @param altM    Altitude above ellipsoid in metres.
     * @param accuracy Horizontal accuracy (metres, 68th percentile).
     * @param timestampNanos Sensor event timestamp in nanoseconds.
     */
    fun updateGnss(
        latRad: Double,
        lonRad: Double,
        altM: Double,
        accuracy: Float,
        timestampNanos: Long,
    ) {
        var s = state

        // Initialise NED origin on first fix.
        if (!s.originInitialised) {
            s = s.copy(
                originLat = latRad,
                originLon = lonRad,
                originAlt = altM,
                originInitialised = true,
                positionNed = doubleArrayOf(0.0, 0.0, 0.0),
            )
        }

        // Convert GNSS position to NED.
        val gnssNed = s.geodeticToNed(latRad, lonRad, altM)

        // Innovation (residual)
        val innovation = doubleArrayOf(
            gnssNed[0] - s.positionNed[0],
            gnssNed[1] - s.positionNed[1],
            gnssNed[2] - s.positionNed[2],
        )
        lastGnssInnovationNorm = sqrt(
            innovation[0] * innovation[0] +
            innovation[1] * innovation[1] +
            innovation[2] * innovation[2]
        )

        // Measurement noise R (isotropic, from reported accuracy)
        val sigma = max(accuracy.toDouble(), 1.0) // floor at 1 m
        val r = Matrix.identity(3) * (sigma * sigma)

        // H = [I₃ | 0₃ₓ₁₂]
        val h = Matrix(3, EsEkfState.STATE_DIM)
        for (i in 0..2) h[i, i] = 1.0

        // Kalman gain
        val ht = h.transpose()
        val sMat = h * s.covariance * ht + r
        val sInv = sMat.inverse()
        val k = s.covariance * ht * sInv

        // Error-state correction
        val dx = k.multiplyVector(innovation)

        // Covariance update: P = (I − K·H) · P
        val kh = k * h
        val iMinusKh = Matrix.identity(EsEkfState.STATE_DIM) - kh
        val newCov = iMinusKh * s.covariance

        // Inject error state into nominal
        state = injectErrorState(s.copy(covariance = newCov), dx)
        lastGnssNanos = timestampNanos
        state = state.copy(lastGnssTimestampMillis = System.currentTimeMillis())
    }

    // ── ZUPT update ─────────────────────────────────────────────────────

    /**
     * Zero-velocity update: constrains velocity to zero when stationary.
     *
     * Observation: v = 0
     * H = [0₃ₓ₃  I₃  0₃ₓ₉]  (3×15, selecting velocity states)
     * R = diag(0.01) — tight constraint.
     */
    fun updateZupt() {
        val s = state
        val innovation = doubleArrayOf(
            -s.velocityNed[0],
            -s.velocityNed[1],
            -s.velocityNed[2],
        )

        val h = Matrix(3, EsEkfState.STATE_DIM)
        for (i in 0..2) h[i, 3 + i] = 1.0

        val r = Matrix.identity(3) * 0.01

        val ht = h.transpose()
        val sMat = h * s.covariance * ht + r
        val sInv = sMat.inverse()
        val k = s.covariance * ht * sInv
        val dx = k.multiplyVector(innovation)
        val kh = k * h
        val newCov = (Matrix.identity(EsEkfState.STATE_DIM) - kh) * s.covariance

        state = injectErrorState(s.copy(covariance = newCov), dx)
    }

    // ── ZARU update ─────────────────────────────────────────────────────

    /**
     * Zero-angular-rate update: when stationary, the measured angular rate
     * should equal the gyro bias. This helps estimate gyro bias.
     *
     * Observation: ω_measured ≈ b_g  ⟹  z = ω_measured − b_g_nominal
     * H = [0₃ₓ₁₂  I₃]  (3×15, selecting gyro-bias states)
     * R = diag(0.001) — tight constraint.
     *
     * @param gyroMeasured Raw gyroscope reading [ωx, ωy, ωz] (rad/s).
     */
    fun updateZaru(gyroMeasured: DoubleArray) {
        val s = state
        val innovation = doubleArrayOf(
            gyroMeasured[0] - s.gyroBias[0],
            gyroMeasured[1] - s.gyroBias[1],
            gyroMeasured[2] - s.gyroBias[2],
        )

        val h = Matrix(3, EsEkfState.STATE_DIM)
        for (i in 0..2) h[i, 12 + i] = 1.0

        val r = Matrix.identity(3) * 0.001

        val ht = h.transpose()
        val sMat = h * s.covariance * ht + r
        val sInv = sMat.inverse()
        val k = s.covariance * ht * sInv
        val dx = k.multiplyVector(innovation)
        val kh = k * h
        val newCov = (Matrix.identity(EsEkfState.STATE_DIM) - kh) * s.covariance

        state = injectErrorState(s.copy(covariance = newCov), dx)
    }

    // ── Non-holonomic constraint (NHC) ──────────────────────────────────

    /**
     * Applies a non-holonomic constraint: lateral and vertical velocity
     * in the body frame should be zero for a ground vehicle.
     *
     * This constrains v_body[1] = 0 (lateral) and v_body[2] = 0 (vertical).
     *
     * Observation: [0, 0]ᵀ = S · C_nb · v_ned  (S selects rows 1,2)
     * H includes coupling through both δv and δθ.
     */
    fun updateNhc() {
        val s = state
        val cBn = s.attitude.toRotationMatrix()
        val cNb = cBn.transpose() // navigation → body

        // Body-frame velocity
        val vBody = cNb.multiplyVector(s.velocityNed)

        // Innovation: want lateral and vertical body velocity to be zero
        val innovation = doubleArrayOf(-vBody[1], -vBody[2])

        // Selection matrix S (2×3): picks rows 1 and 2
        val selectMat = Matrix(2, 3)
        selectMat[0, 1] = 1.0  // lateral
        selectMat[1, 2] = 1.0  // vertical

        // H (2×15)
        val h = Matrix(2, EsEkfState.STATE_DIM)

        // ∂h/∂δv = S · C_nb  (2×3, maps to columns 3–5)
        val sCnb = selectMat * cNb
        for (i in 0..1) for (j in 0..2) h[i, 3 + j] = sCnb[i, j]

        // ∂h/∂δθ = S · C_nb · [v_ned]×  (2×3, maps to columns 6–8)
        val vSkew = Matrix.skewSymmetric(s.velocityNed)
        val sCnbVskew = selectMat * cNb * vSkew
        for (i in 0..1) for (j in 0..2) h[i, 6 + j] = sCnbVskew[i, j]

        // Measurement noise — moderate constraint
        val r = Matrix.identity(2) * 0.1

        val ht = h.transpose()
        val sMat = h * s.covariance * ht + r
        val sInv = sMat.inverse()
        val k = s.covariance * ht * sInv
        val dx = k.multiplyVector(innovation)
        val kh = k * h
        val newCov = (Matrix.identity(EsEkfState.STATE_DIM) - kh) * s.covariance

        state = injectErrorState(s.copy(covariance = newCov), dx)
    }

    // ── Barometric altitude update ──────────────────────────────────────

    /**
     * Applies a relative barometric altitude measurement update.
     *
     * z = Δalt_baro (positive = went up)
     * The predicted altitude change maps to -δp_D (NED down positive).
     * H = [0, 0, -1, 0...0]  (1×15)
     * R = R_BARO = 0.09 m²  ((0.3 m)²)
     *
     * @param deltaAlt Relative altitude change from the [BaroFilter] (metres).
     * @param predictedDeltaDown Change in the EKF's NED-down position
     *                           since the last accepted baro reading.
     */
    fun updateBaroAltitude(deltaAlt: Double, predictedDeltaDown: Double) {
        val s = state

        // Innovation: measured altitude change vs predicted
        // Baro reports altitude up; NED-D is positive down.
        // Predicted altitude change (up) = -Δp_D
        val predictedAltChange = -predictedDeltaDown
        val innovation = doubleArrayOf(deltaAlt - predictedAltChange)

        // H (1×15): ∂(altitude)/∂(δp_D) = -1
        val h = Matrix(1, EsEkfState.STATE_DIM)
        h[0, 2] = -1.0  // position-down component

        val r = Matrix(1, 1)
        r[0, 0] = BaroFilter.R_BARO

        val ht = h.transpose()
        val sMat = h * s.covariance * ht + r
        val sInv = sMat.inverse()
        val k = s.covariance * ht * sInv
        val dx = k.multiplyVector(innovation)
        val kh = k * h
        val newCov = (Matrix.identity(EsEkfState.STATE_DIM) - kh) * s.covariance

        state = injectErrorState(s.copy(covariance = newCov), dx)
    }

    // ── Confidence score ────────────────────────────────────────────────

    /**
     * Computes a 0–100 "position confidence" score for the UI.
     *
     * ## Mapping
     * ```
     * σ = sqrt(P[0,0] + P[1,1] + P[2,2])   // 1σ position uncertainty (m)
     * base = clamp(100 − σ × 4, 0, 100)      // 25 m → 0 confidence
     * gnss_penalty:
     *   age > 30 s → −20
     *   age > 10 s → −10
     *   else       →  0
     * innovation_penalty:
     *   last_gnss_innovation > 3σ → −15
     *   else → 0
     * confidence = clamp(base + gnss_penalty + innovation_penalty, 0, 100)
     * ```
     */
    fun computeConfidence(): Int {
        val p = state.covariance
        val posTrace = p[0, 0] + p[1, 1] + p[2, 2]
        val sigma = sqrt(max(posTrace, 0.0))

        var score = (100.0 - sigma * 4.0).coerceIn(0.0, 100.0)

        // GNSS age penalty
        val gnssAgeMs = if (state.lastGnssTimestampMillis > 0) {
            System.currentTimeMillis() - state.lastGnssTimestampMillis
        } else {
            Long.MAX_VALUE
        }
        val gnssAgeSec = gnssAgeMs / 1000.0
        score += when {
            gnssAgeSec > 30.0 -> -20.0
            gnssAgeSec > 10.0 -> -10.0
            else -> 0.0
        }

        // Innovation penalty
        if (lastGnssInnovationNorm > sigma * 3.0 && sigma > 0.1) {
            score -= 15.0
        }

        return score.coerceIn(0.0, 100.0).toInt()
    }

    // ── Error-state injection ───────────────────────────────────────────

    /**
     * Injects the error state δx into the nominal state and resets δx to zero.
     *
     * - Position:  p ← p + δp
     * - Velocity:  v ← v + δv
     * - Attitude:  q ← q ⊗ Δq(δθ)
     * - Biases:    b ← b + δb
     */
    private fun injectErrorState(s: EsEkfState, dx: DoubleArray): EsEkfState {
        val newPos = doubleArrayOf(
            s.positionNed[0] + dx[0],
            s.positionNed[1] + dx[1],
            s.positionNed[2] + dx[2],
        )
        val newVel = doubleArrayOf(
            s.velocityNed[0] + dx[3],
            s.velocityNed[1] + dx[4],
            s.velocityNed[2] + dx[5],
        )
        val dTheta = doubleArrayOf(dx[6], dx[7], dx[8])
        val dq = Quaternion.fromRotationVector(dTheta)
        val newAtt = (s.attitude * dq).normalize()

        val newAccelBias = doubleArrayOf(
            s.accelBias[0] + dx[9],
            s.accelBias[1] + dx[10],
            s.accelBias[2] + dx[11],
        )
        val newGyroBias = doubleArrayOf(
            s.gyroBias[0] + dx[12],
            s.gyroBias[1] + dx[13],
            s.gyroBias[2] + dx[14],
        )

        return s.copy(
            positionNed = newPos,
            velocityNed = newVel,
            attitude = newAtt,
            accelBias = newAccelBias,
            gyroBias = newGyroBias,
        )
    }

    /** Resets the filter to initial state. */
    fun reset() {
        state = EsEkfState()
        lastGnssNanos = 0L
        lastGnssInnovationNorm = 0.0
        currentMotionMode = MotionMode.STOPPED
    }
}
