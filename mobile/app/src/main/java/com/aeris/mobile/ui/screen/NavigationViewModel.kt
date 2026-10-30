package com.aeris.mobile.ui.screen

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aeris.mobile.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import java.net.URLEncoder
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A decoded geographic coordinate, used for destination and route waypoints.
 */
data class GeoPoint(val lat: Double, val lon: Double)

/**
 * A single geocoding result (place name + coordinates).
 */
data class GeocoderResult(val name: String, val point: GeoPoint)

/**
 * A single parsed route step (maneuver instruction + bearing after).
 */
data class RouteStep(
    val instruction: String,
    val distanceMeters: Double,
    val bearingAfter: Double,   // degrees, 0 = north
    val startPoint: GeoPoint,
)

/**
 * Encapsulates all navigation-specific UI state:
 * - Origin search / geocoding (arbitrary "from" location or live GPS)
 * - Destination search / geocoding
 * - Resolved route waypoints (decoded from Mapbox Directions API)
 * - ETA / distance
 * - Next-maneuver banner data
 */
class NavigationViewModel(application: Application) : AndroidViewModel(application) {

    // ── Simulation Engine ────────────────────────────────────────────────
    val simulationEngine = com.aeris.mobile.core.simulation.SimulationEngine(application)
    var isSimulationMode by mutableStateOf(false)
        private set

    // ── Origin ───────────────────────────────────────────────────────────
    /** null = "use live GPS position". Set when the user picks a custom origin. */
    var origin by mutableStateOf<GeoPoint?>(null)
        private set
    var originName by mutableStateOf<String?>(null)
        private set
    var originQuery by mutableStateOf("")
    var originResults by mutableStateOf<List<GeocoderResult>>(emptyList())
    var isOriginGeocoding by mutableStateOf(false)

    // ── Destination ──────────────────────────────────────────────────────
    var destination by mutableStateOf<GeoPoint?>(null)
        private set
    var destinationName by mutableStateOf<String?>(null)
        private set

    // ── Geocoder (destination) ────────────────────────────────────────────
    var searchQuery by mutableStateOf("")
    var geocoderResults by mutableStateOf<List<GeocoderResult>>(emptyList())
    var isGeocoding by mutableStateOf(false)
    var geocodeError by mutableStateOf<String?>(null)

    // ── Route ────────────────────────────────────────────────────────────
    /** Decoded route polyline from Mapbox Directions API. */
    var routeWaypoints by mutableStateOf<List<GeoPoint>>(emptyList())
        private set
    var isRouteFetching by mutableStateOf(false)
    var routeError by mutableStateOf<String?>(null)

    /** Parsed steps for turn-by-turn guidance. */
    var routeSteps by mutableStateOf<List<RouteStep>>(emptyList())
        private set

    // ── ETA / distance ───────────────────────────────────────────────────
    var etaMinutes by mutableStateOf<Int?>(null)
        private set
    var remainingDistanceMeters by mutableStateOf<Double?>(null)
        private set
    /** Full route distance from origin to destination (metres). */
    var totalRouteDistanceMeters by mutableStateOf<Double?>(null)
        private set

    // ── Next maneuver ────────────────────────────────────────────────────
    var nextManeuver by mutableStateOf<String?>(null)
        private set
    var nextManeuverDistanceM by mutableStateOf<Double?>(null)
        private set

    // ── Current heading for 3-D camera ───────────────────────────────────
    /** Bearing from the active route step (degrees, 0 = north). */
    var routeBearing by mutableStateOf(0.0)
        private set

    // ── Navigation panel visibility ──────────────────────────────────────
    var isNavigating by mutableStateOf(false)
        private set

    private var geocodeJob: Job? = null
    private var originGeocodeJob: Job? = null
    private var routeJob: Job? = null

    // ── Public API ────────────────────────────────────────────────────────

    // --- Destination search ---

    fun onSearchQueryChange(q: String) {
        searchQuery = q
        if (q.length >= 3) geocode(q) else geocoderResults = emptyList()
    }

    fun selectDestination(result: GeocoderResult) {
        destination = result.point
        destinationName = result.name
        searchQuery = result.name
        geocoderResults = emptyList()
        isNavigating = false // will be set true once route is fetched
    }

    // --- Origin search ---

    fun onOriginQueryChange(q: String) {
        originQuery = q
        if (q.length >= 3) geocodeOrigin(q) else originResults = emptyList()
    }

    fun selectOrigin(result: GeocoderResult) {
        origin = result.point
        originName = result.name
        originQuery = result.name
        originResults = emptyList()
    }

    fun clearOrigin() {
        origin = null
        originName = null
        originQuery = ""
        originResults = emptyList()
        isSimulationMode = false
        simulationEngine.stopSimulation()
    }

    fun swapOriginAndDestination() {
        val tempDest = destination
        val tempDestName = destinationName
        
        destination = origin
        destinationName = originName
        searchQuery = originName ?: ""
        
        origin = tempDest
        originName = tempDestName
        originQuery = tempDestName ?: ""
        
        // Clear route and geocoding results when swapped
        routeWaypoints = emptyList()
        routeSteps = emptyList()
        etaMinutes = null
        remainingDistanceMeters = null
        totalRouteDistanceMeters = null
        nextManeuver = null
        nextManeuverDistanceM = null
        routeBearing = 0.0
        isNavigating = false
        geocoderResults = emptyList()
        originResults = emptyList()
        isSimulationMode = false
        simulationEngine.stopSimulation()
    }

    // --- Routing ---

    /**
     * Fetch a route. [gpsLat]/[gpsLon] are the live device position — used as
     * origin fallback when the user has not set a custom origin.
     */
    fun startRouting(gpsLat: Double, gpsLon: Double) {
        val dest = destination ?: return
        val oLat = origin?.lat ?: gpsLat
        val oLon = origin?.lon ?: gpsLon
        fetchRoute(oLat, oLon, dest.lat, dest.lon)
    }

    fun clearDestination() {
        destination = null
        destinationName = null
        routeWaypoints = emptyList()
        routeSteps = emptyList()
        etaMinutes = null
        remainingDistanceMeters = null
        totalRouteDistanceMeters = null
        nextManeuver = null
        nextManeuverDistanceM = null
        routeBearing = 0.0
        isNavigating = false
        isSimulationMode = false
        simulationEngine.stopSimulation()
        geocoderResults = emptyList()
        searchQuery = ""
    }

    fun updateRemainingDistance(currentLat: Double, currentLon: Double) {
        val dest = destination ?: return
        remainingDistanceMeters = haversine(currentLat, currentLon, dest.lat, dest.lon)

        // Advance the next-maneuver banner based on current position.
        if (routeSteps.isNotEmpty()) {
            val nextStep = routeSteps.minByOrNull {
                haversine(currentLat, currentLon, it.startPoint.lat, it.startPoint.lon)
            }
            if (nextStep != null) {
                nextManeuver = nextStep.instruction
                nextManeuverDistanceM = haversine(
                    currentLat, currentLon,
                    nextStep.startPoint.lat, nextStep.startPoint.lon,
                )
                routeBearing = nextStep.bearingAfter
            }
        }
    }

    // ── Simulation Mode ──────────────────────────────────────────────────
    
    fun startSimulationRoute() {
        isSimulationMode = true
        // Hardcode destinations for the demo
        originName = "Simulation Start"
        destinationName = "Simulation End"
        origin = GeoPoint(52.3704499, -1.2544378) // roughly from dataset
        destination = GeoPoint(52.3784781, -1.2596625) 
        
        // Fetch the road path so we have a white dashed line from start to end
        fetchRoute(origin!!.lat, origin!!.lon, destination!!.lat, destination!!.lon)

        viewModelScope.launch {
            simulationEngine.startSimulation(speedMultiplier = 10)
        }
    }

    // ── Private helpers ──────────────────────────────────────────────────

    private fun geocode(query: String) {
        geocodeJob?.cancel()
        geocodeJob = viewModelScope.launch {
            isGeocoding = true
            geocodeError = null
            try {
                geocoderResults = fetchGeocodeResults(query)
            } catch (e: Exception) {
                geocodeError = "Could not search: ${e.message}"
            } finally {
                isGeocoding = false
            }
        }
    }

    private fun geocodeOrigin(query: String) {
        originGeocodeJob?.cancel()
        originGeocodeJob = viewModelScope.launch {
            isOriginGeocoding = true
            try {
                originResults = fetchGeocodeResults(query)
            } catch (_: Exception) {
                // Silently fail for origin search
            } finally {
                isOriginGeocoding = false
            }
        }
    }

    private suspend fun fetchGeocodeResults(query: String): List<GeocoderResult> {
        val encoded = URLEncoder.encode(query, "UTF-8")
        val token = BuildConfig.MAPBOX_PUBLIC_TOKEN
        val url =
            "https://api.mapbox.com/geocoding/v5/mapbox.places/$encoded.json" +
                    "?access_token=$token&limit=5&types=place,address,poi"
        val json = withContext(Dispatchers.IO) { URL(url).readText() }
        val root = JSONObject(json)
        val features = root.getJSONArray("features")
        val results = mutableListOf<GeocoderResult>()
        for (i in 0 until features.length()) {
            val feat = features.getJSONObject(i)
            val name = feat.getString("place_name")
            val coords = feat.getJSONObject("geometry").getJSONArray("coordinates")
            results += GeocoderResult(
                name = name,
                point = GeoPoint(lat = coords.getDouble(1), lon = coords.getDouble(0)),
            )
        }
        return results
    }

    private fun fetchRoute(
        originLat: Double, originLon: Double,
        destLat: Double, destLon: Double,
    ) {
        routeJob?.cancel()
        routeJob = viewModelScope.launch {
            isRouteFetching = true
            routeError = null
            isNavigating = false
            try {
                val token = BuildConfig.MAPBOX_PUBLIC_TOKEN
                val coords = "$originLon,$originLat;$destLon,$destLat"
                val url =
                    "https://api.mapbox.com/directions/v5/mapbox/driving/$coords" +
                            "?access_token=$token&geometries=geojson&overview=full&steps=true"
                val json = withContext(Dispatchers.IO) { URL(url).readText() }
                val root = JSONObject(json)
                val routes = root.getJSONArray("routes")
                if (routes.length() == 0) {
                    routeError = "No route found"
                    return@launch
                }
                val route = routes.getJSONObject(0)
                val distanceM = route.getDouble("distance")
                val durationSec = route.getDouble("duration")

                // Overview polyline
                val geom = route.getJSONObject("geometry")
                val coordsArr = geom.getJSONArray("coordinates")
                val waypoints = mutableListOf<GeoPoint>()
                for (i in 0 until coordsArr.length()) {
                    val c = coordsArr.getJSONArray(i)
                    waypoints += GeoPoint(lat = c.getDouble(1), lon = c.getDouble(0))
                }

                // Parse steps for turn-by-turn guidance
                val parsedSteps = mutableListOf<RouteStep>()
                val legsArray = route.getJSONArray("legs")
                for (li in 0 until legsArray.length()) {
                    val leg = legsArray.getJSONObject(li)
                    val stepsArray = leg.getJSONArray("steps")
                    for (si in 0 until stepsArray.length()) {
                        val step = stepsArray.getJSONObject(si)
                        val maneuver = step.getJSONObject("maneuver")
                        val instruction = maneuver.optString("instruction", "Continue")
                        val bearingAfter = maneuver.optDouble("bearing_after", 0.0)
                        val stepDist = step.getDouble("distance")
                        val loc = maneuver.getJSONArray("location")
                        parsedSteps += RouteStep(
                            instruction = instruction,
                            distanceMeters = stepDist,
                            bearingAfter = bearingAfter,
                            startPoint = GeoPoint(lat = loc.getDouble(1), lon = loc.getDouble(0)),
                        )
                    }
                }

                routeWaypoints = waypoints
                routeSteps = parsedSteps
                remainingDistanceMeters = distanceM
                totalRouteDistanceMeters = distanceM
                etaMinutes = (durationSec / 60.0).roundToInt().coerceAtLeast(1)

                // Seed the first maneuver
                parsedSteps.firstOrNull()?.let { first ->
                    nextManeuver = first.instruction
                    nextManeuverDistanceM = first.distanceMeters
                    routeBearing = first.bearingAfter
                }
                isNavigating = true
            } catch (e: Exception) {
                routeError = "Route unavailable: ${e.message}"
            } finally {
                isRouteFetching = false
            }
        }
    }

    private fun haversine(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
                cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
                sin(dLon / 2) * sin(dLon / 2)
        return 2 * r * atan2(sqrt(a), sqrt(1 - a))
    }
}
