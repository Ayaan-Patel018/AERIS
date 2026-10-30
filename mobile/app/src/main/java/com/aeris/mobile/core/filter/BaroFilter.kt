package com.aeris.mobile.core.filter

/**
 * Rolling-window barometric altitude filter.
 *
 * Maintains the last [WINDOW_SIZE] barometer altitude readings and
 * exposes:
 * - Whether the readings are stable (low variance) — only then is a
 *   baro measurement update applied to the EKF.
 * - The relative altitude change since the last accepted reading,
 *   used as the baro measurement z_baro = alt_now − alt_prev.
 *
 * ## Noise model
 * R_baro = (0.3 m)² = 0.09 m² — see [EsEkf.updateBaroAltitude].
 */
class BaroFilter {

    companion object {
        /** Number of readings in the stability-check window. */
        const val WINDOW_SIZE = 5

        /**
         * Maximum altitude variance (m²) for the window to be considered
         * stable. If exceeded, the baro update is skipped.
         */
        const val STABILITY_VARIANCE_THRESHOLD = 0.5

        /** Measurement noise R for the baro update (m²). */
        const val R_BARO = 0.09  // (0.3 m)²
    }

    private val altitudeWindow = ArrayDeque<Double>(WINDOW_SIZE + 1)

    /** The last altitude value that was accepted into an EKF update. */
    private var lastAcceptedAltitude: Double? = null

    /**
     * Pushes a new barometric altitude reading (metres).
     */
    fun addSample(altitudeMetres: Double) {
        altitudeWindow.addLast(altitudeMetres)
        if (altitudeWindow.size > WINDOW_SIZE) altitudeWindow.removeFirst()
    }

    /**
     * Returns `true` if the current window has at least [WINDOW_SIZE]
     * samples and the altitude variance is below [STABILITY_VARIANCE_THRESHOLD].
     */
    fun isStable(): Boolean {
        if (altitudeWindow.size < WINDOW_SIZE) return false
        return ZuptDetector.variance(altitudeWindow.toList()) < STABILITY_VARIANCE_THRESHOLD
    }

    /**
     * Returns the relative altitude change since the last accepted
     * reading. Returns `null` if no previous reading has been accepted
     * or if the window is not yet full.
     *
     * Call [markAccepted] after applying the EKF update.
     */
    fun deltaAltitude(): Double? {
        if (altitudeWindow.isEmpty()) return null
        val current = altitudeWindow.last()
        val prev = lastAcceptedAltitude ?: return null
        return current - prev
    }

    /**
     * Marks the current altitude as accepted (i.e. it was used in an
     * EKF measurement update). Future [deltaAltitude] calls will be
     * relative to this value.
     */
    fun markAccepted() {
        if (altitudeWindow.isNotEmpty()) {
            lastAcceptedAltitude = altitudeWindow.last()
        }
    }

    /** Resets all state — call when tracking restarts. */
    fun reset() {
        altitudeWindow.clear()
        lastAcceptedAltitude = null
    }
}
