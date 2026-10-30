package com.aeris.mobile.core.sensor

import android.annotation.SuppressLint
import android.content.Context
import android.os.Looper
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Collects GNSS position fixes via Google Play Services'
 * [FusedLocationProviderClient] and emits them as a [Flow] of [GnssSample].
 *
 * The location request runs at 1 Hz with high accuracy priority, matching
 * the typical GNSS update rate. When the provider has no fix (e.g.
 * indoors), the flow simply stops emitting — the [TrackingService]
 * interprets the absence of recent samples as a GNSS outage.
 */
class GnssCollector(private val context: Context) {

    /**
     * Starts requesting GNSS fixes. Requires [android.Manifest.permission.ACCESS_FINE_LOCATION].
     *
     * The returned [Flow] is cold — location updates begin when collected
     * and stop when the collector is cancelled.
     */
    @SuppressLint("MissingPermission") // Caller ensures permission is granted.
    fun samples(): Flow<GnssSample> = callbackFlow {
        val client: FusedLocationProviderClient =
            LocationServices.getFusedLocationProviderClient(context)

        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            1_000L // 1 Hz interval
        ).setMinUpdateIntervalMillis(500L).build()

        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val location = result.lastLocation ?: return
                val sample = GnssSample(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    altitude = location.altitude,
                    accuracy = location.accuracy,
                    speed = location.speed,
                    bearing = location.bearing,
                    timestampMillis = location.time,
                )
                trySend(sample)
            }
        }

        client.requestLocationUpdates(request, callback, Looper.getMainLooper())

        awaitClose {
            client.removeLocationUpdates(callback)
        }
    }
}
