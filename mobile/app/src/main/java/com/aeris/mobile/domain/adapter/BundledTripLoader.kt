package com.aeris.mobile.domain.adapter

import android.content.Context
import com.aeris.mobile.domain.model.Drive
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Thin asset loader for the bundled aeris-trip/1 drive. All parsing is in [AerisTripAdapter].
 * The metrics file is optional; without it the app shows "—" for every scored number.
 */
object BundledTripLoader {

    const val TRIP_ASSET = "S3b_aeris_trip_v1.json"
    const val METRICS_ASSET = "S3b_metrics.json"

    suspend fun load(context: Context): Drive = withContext(Dispatchers.IO) {
        val drive = AerisTripAdapter.parse(readAsset(context, TRIP_ASSET))
        val metrics = try {
            AerisTripAdapter.parseMetrics(readAsset(context, METRICS_ASSET))
        } catch (e: Exception) {
            null
        }
        drive.copy(metrics = metrics, meta = drive.meta.copy(metricsAvailable = metrics != null))
    }

    private fun readAsset(context: Context, name: String): String =
        context.assets.open(name).bufferedReader().use { it.readText() }
}
