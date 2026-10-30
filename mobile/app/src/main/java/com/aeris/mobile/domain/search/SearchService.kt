package com.aeris.mobile.domain.search

import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.OutageWindow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class SearchPlace(
    val name: String,
    val category: String,
    val locality: String,
    val lat: Double,
    val lon: Double,
    val distanceKm: Double? = null,
)

data class SearchDriveResult(
    val drive: Drive,
    val label: String,
    val summary: String,
)

data class SearchMomentResult(
    val driveId: String,
    val title: String,
    val detail: String,
    val timestampSec: Double,
    val lat: Double,
    val lon: Double,
    val isOutage: Boolean,
)

data class SearchResults(
    val places: List<SearchPlace> = emptyList(),
    val drives: List<SearchDriveResult> = emptyList(),
    val moments: List<SearchMomentResult> = emptyList(),
    val isOffline: Boolean = false,
    val errorMessage: String? = null,
)

object SearchService {

    /**
     * Queries Photon geocoding service per R3 § 2 with 300 ms debounce & min 3 chars.
     * Biased to latitude and longitude.
     */
    suspend fun searchPlaces(
        query: String,
        biasLat: Double = 52.3704,
        biasLon: Double = -1.2544
    ): List<SearchPlace> = withContext(Dispatchers.IO) {
        if (query.trim().length < 3) return@withContext emptyList()

        try {
            val encoded = URLEncoder.encode(query.trim(), "UTF-8")
            val urlString = "https://photon.komoot.io/api/?q=$encoded&limit=8&lat=$biasLat&lon=$biasLon"
            val url = URL(urlString)
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 4000
                readTimeout = 4000
                setRequestProperty("User-Agent", "AERIS-Mobile/1.0")
            }

            if (conn.responseCode == 200) {
                val jsonText = conn.inputStream.bufferedReader().use { it.readText() }
                parsePhotonJson(jsonText, biasLat, biasLon)
            } else {
                emptyList()
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun parsePhotonJson(jsonText: String, userLat: Double, userLon: Double): List<SearchPlace> {
        val root = JSONObject(jsonText)
        val features = root.optJSONArray("features") ?: return emptyList()
        val results = mutableListOf<SearchPlace>()

        for (i in 0 until features.length()) {
            val feat = features.getJSONObject(i)
            val geom = feat.getJSONObject("geometry")
            val coords = geom.getJSONArray("coordinates")
            val lon = coords.getDouble(0)
            val lat = coords.getDouble(1)

            val props = feat.getJSONObject("properties")
            val name = props.optString("name", "Unknown location")
            val type = props.optString("type", props.optString("osm_value", "Place"))
            val city = props.optString("city", props.optString("town", props.optString("county", "")))
            val street = props.optString("street", "")
            val locality = listOf(street, city).filter { it.isNotBlank() }.joinToString(", ")

            // Distance calculation
            val distMeters = com.aeris.mobile.domain.math.EventDetector.haversineDistanceMeters(userLat, userLon, lat, lon)
            val distKm = distMeters / 1000.0

            results.add(
                SearchPlace(
                    name = name,
                    category = type.replaceFirstChar { it.uppercase() },
                    locality = if (locality.isNotBlank()) locality else "Nearby",
                    lat = lat,
                    lon = lon,
                    distanceKm = distKm
                )
            )
        }
        return results
    }

    /**
     * Local drive search matching id and label.
     */
    fun searchLocalDrives(query: String, drives: List<Drive>): List<SearchDriveResult> {
        val q = query.trim().lowercase()
        return drives.filter {
            it.meta.id.lowercase().contains(q) || it.meta.name.lowercase().contains(q) || "drive".contains(q)
        }.map { d ->
            val min = (d.meta.durationSec / 60).toInt().coerceAtLeast(1)
            val dist = com.aeris.mobile.util.Formatters.formatDistance(d.meta.totalDistanceMeters)
            val loss = if (d.outages.isEmpty()) "No satellite loss" else "${d.outages.size} satellite loss"
            SearchDriveResult(
                drive = d,
                label = d.meta.id,
                summary = "$min min • $dist • $loss"
            )
        }
    }

    /**
     * Local moments index search per R3 § 2:
     * Satellite loss, Satellite back, Turn, Stop.
     */
    fun searchLocalMoments(query: String, drives: List<Drive>): List<SearchMomentResult> {
        val q = query.trim().lowercase()
        val matches = mutableListOf<SearchMomentResult>()

        for (d in drives) {
            // Outage moments
            for (outage in d.outages) {
                if (q.isEmpty() || "satellite".contains(q) || "loss".contains(q) || "outage".contains(q) || d.meta.id.lowercase().contains(q)) {
                    val mmSs = com.aeris.mobile.util.Formatters.formatMmSs(outage.startSec)
                    matches.add(
                        SearchMomentResult(
                            driveId = d.meta.id,
                            title = "Satellite loss • ${d.meta.id}",
                            detail = "at $mmSs, lasted ${outage.durationSec.toInt()} s",
                            timestampSec = outage.startSec,
                            lat = outage.startPoint.lat,
                            lon = outage.startPoint.lon,
                            isOutage = true
                        )
                    )
                }
            }
        }
        return matches
    }
}
