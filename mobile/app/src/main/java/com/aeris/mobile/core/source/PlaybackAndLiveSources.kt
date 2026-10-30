package com.aeris.mobile.core.source

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

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
