package com.aeris.mobile.core.source

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.SystemClock
import androidx.core.content.ContextCompat
import com.aeris.mobile.permissions.PermissionManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Real Phone GNSS Source using Android's native GPS_PROVIDER (satellite fixes only) per R3 § 3.
 *
 * It avoids FusedLocationProvider so that satellite loss is never masked by Wi-Fi/cell triangulation.
 */
class PhoneGnssSource(
    private val context: Context,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main),
) : PositionSource {

    private val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
    private val _state = MutableStateFlow<PositionState?>(null)
    override val state: StateFlow<PositionState?> = _state.asStateFlow()

    private var lastFixElapsedRealtimeMs = 0L
    private var isRunning = false
    private var healthCheckJob: Job? = null

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(loc: Location) {
            lastFixElapsedRealtimeMs = SystemClock.elapsedRealtime()
            _state.value = PositionState(
                lat = loc.latitude,
                lon = loc.longitude,
                headingDeg = if (loc.hasBearing()) loc.bearing.toDouble() else null,
                speedMps = if (loc.hasSpeed()) loc.speed.toDouble() else null,
                sigma = null,
                signal = SignalState.Locked,
                source = SourceKind.PhoneGnss,
                accuracyM = if (loc.hasAccuracy()) loc.accuracy else null
            )
        }

        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {
            if (provider == LocationManager.GPS_PROVIDER) {
                _state.value = _state.value?.copy(signal = SignalState.Unknown)
            }
        }
        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    }

    @SuppressLint("MissingPermission")
    override fun start() {
        if (isRunning) return
        if (locationManager == null || !PermissionManager.hasFineLocation(context)) {
            _state.value = PositionState(
                lat = 52.3704,
                lon = -1.2544,
                headingDeg = null,
                speedMps = null,
                sigma = null,
                signal = SignalState.Unknown,
                source = SourceKind.PhoneGnss
            )
            return
        }

        isRunning = true
        _state.value = PositionState(
            lat = 52.3704,
            lon = -1.2544,
            headingDeg = null,
            speedMps = null,
            sigma = null,
            signal = SignalState.Searching,
            source = SourceKind.PhoneGnss
        )

        try {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1000L, // 1 Hz
                0f,
                locationListener,
                context.mainLooper
            )
        } catch (e: Exception) {
            _state.value = _state.value?.copy(signal = SignalState.Unknown)
        }

        // Start health monitor: If no fix for > 5s after having received one, transition to Lost per R3 § 3
        healthCheckJob?.cancel()
        healthCheckJob = scope.launch {
            while (isActive && isRunning) {
                delay(1000L)
                if (lastFixElapsedRealtimeMs > 0L) {
                    val ageMs = SystemClock.elapsedRealtime() - lastFixElapsedRealtimeMs
                    if (ageMs > 5000L && _state.value?.signal == SignalState.Locked) {
                        _state.value = _state.value?.copy(signal = SignalState.Lost)
                    }
                }
            }
        }
    }

    override fun stop() {
        isRunning = false
        healthCheckJob?.cancel()
        healthCheckJob = null
        try {
            locationManager?.removeUpdates(locationListener)
        } catch (_: Exception) {}
    }
}
