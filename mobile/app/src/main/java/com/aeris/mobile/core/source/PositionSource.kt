package com.aeris.mobile.core.source

import kotlinx.coroutines.flow.StateFlow

data class Sigma(
    val semiMajorM: Double,
    val semiMinorM: Double,
    val orientationDeg: Double
)

enum class SignalState {
    Locked,
    Lost,
    Searching,
    Unknown
}

enum class SourceKind {
    PhoneGnss,
    TripPlayback,
    AerisLive
}

/**
 * Universal position state consumed by all navigation and explore screens per R1 § 2.
 */
data class PositionState(
    val lat: Double,
    val lon: Double,
    val headingDeg: Double?,
    val speedMps: Double?,
    val sigma: Sigma?,
    val signal: SignalState,
    val source: SourceKind,
    val tSeconds: Double? = null,
    val accuracyM: Float? = null,
)

/**
 * Universal interface for all position sources (Phone satellite GPS, Trip playback, and AerisLive).
 */
interface PositionSource {
    val state: StateFlow<PositionState?>
    fun start()
    fun stop()
}
