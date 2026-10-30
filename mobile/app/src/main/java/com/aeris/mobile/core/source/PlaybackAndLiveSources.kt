package com.aeris.mobile.core.source

import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.playback.PlaybackClock
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Trip Playback source feeding PositionState from PlaybackClock per R1 § 2.
 */
class TripPlaybackSource(
    private val clock: PlaybackClock,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main),
) : PositionSource {

    private val _state = MutableStateFlow<PositionState?>(null)
    override val state: StateFlow<PositionState?> = _state.asStateFlow()

    private var collectJob: Job? = null

    override fun start() {
        collectJob?.cancel()
        collectJob = scope.launch {
            clock.currentPoint.collect { pt ->
                if (pt != null) {
                    val sig = when (pt.status) {
                        GnssStatus.HEALTHY -> SignalState.Locked
                        GnssStatus.OUTAGE, GnssStatus.DEGRADED -> SignalState.Lost
                        GnssStatus.UNKNOWN -> SignalState.Unknown
                    }

                    val sigmaObj = if (pt.sigma != null) {
                        Sigma(
                            semiMajorM = pt.sigma,
                            semiMinorM = (pt.sigma * 0.75).coerceAtLeast(0.1),
                            orientationDeg = pt.headingDeg ?: 0.0
                        )
                    } else null

                    _state.value = PositionState(
                        lat = pt.lat,
                        lon = pt.lon,
                        headingDeg = pt.headingDeg,
                        speedMps = pt.speedMps,
                        sigma = sigmaObj,
                        signal = sig,
                        source = SourceKind.TripPlayback,
                        tSeconds = pt.timestampSec,
                        accuracyM = pt.sigma?.toFloat()
                    )
                }
            }
        }
    }

    override fun stop() {
        collectJob?.cancel()
        collectJob = null
    }
}

/**
 * Disabled stub for future on-device Python filter port per R1 § 2.
 */
class AerisLiveSource : PositionSource {
    private val _state = MutableStateFlow<PositionState?>(null)
    override val state: StateFlow<PositionState?> = _state.asStateFlow()

    override fun start() {
        // Disabled stub: The filter is Python; interface exists, UI shows disabled state per R1 § 2
        _state.value = PositionState(
            lat = 0.0,
            lon = 0.0,
            headingDeg = null,
            speedMps = null,
            sigma = null,
            signal = SignalState.Unknown,
            source = SourceKind.AerisLive
        )
    }

    override fun stop() {}
}
