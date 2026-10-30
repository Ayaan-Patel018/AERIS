package com.aeris.mobile.core.simulation

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.io.BufferedReader
import java.io.InputStreamReader

data class TrajectoryPoint(
    val lat: Double,
    val lon: Double,
    val heading: Double,
    val t: Double,
    val isGnssHealthy: Boolean = true,
    val velocity: Double = 0.0,
    val uncertainty: Double = 0.0,
    val covXX: Double = 0.0,
    val covYY: Double = 0.0,
    val covXY: Double = 0.0,
)

class SimulationEngine(private val context: Context) {

    private val _simulatedFusedPoint = MutableStateFlow<TrajectoryPoint?>(null)
    val simulatedFusedPoint: StateFlow<TrajectoryPoint?> = _simulatedFusedPoint.asStateFlow()

    private val _simulatedGnssPoint = MutableStateFlow<TrajectoryPoint?>(null)
    val simulatedGnssPoint: StateFlow<TrajectoryPoint?> = _simulatedGnssPoint.asStateFlow()

    private val _simulatedFusedTrace = MutableStateFlow<List<TrajectoryPoint>>(emptyList())
    val simulatedFusedTrace: StateFlow<List<TrajectoryPoint>> = _simulatedFusedTrace.asStateFlow()

    private val _simulatedGnssTrace = MutableStateFlow<List<TrajectoryPoint>>(emptyList())
    val simulatedGnssTrace: StateFlow<List<TrajectoryPoint>> = _simulatedGnssTrace.asStateFlow()

    private val _isRunning = MutableStateFlow(false)
    val isRunning: StateFlow<Boolean> = _isRunning.asStateFlow()

    // Full loaded datasets
    private var fusedData: List<TrajectoryPoint> = emptyList()
    private var gnssData: List<TrajectoryPoint> = emptyList()

    suspend fun loadData() = withContext(Dispatchers.IO) {
        if (fusedData.isNotEmpty() && gnssData.isNotEmpty()) return@withContext

        try {
            fusedData = parseJsonFile("fused_output.json")
            gnssData = parseJsonFile("gnss_only.json")
            Log.d("SimulationEngine", "Loaded ${fusedData.size} fused points, ${gnssData.size} GNSS points")
        } catch (e: Exception) {
            Log.e("SimulationEngine", "Failed to load simulation data", e)
        }
    }

    private fun parseJsonFile(filename: String): List<TrajectoryPoint> {
        val points = mutableListOf<TrajectoryPoint>()
        val inputStream = context.assets.open(filename)
        val reader = BufferedReader(InputStreamReader(inputStream))
        val jsonString = reader.readText()
        reader.close()

        val jsonArray = JSONArray(jsonString)
        for (i in 0 until jsonArray.length()) {
            val obj = jsonArray.getJSONObject(i)
            val status = if (obj.has("status")) obj.getString("status") else "healthy"
            points.add(
                TrajectoryPoint(
                    lat = obj.getDouble("lat"),
                    lon = obj.getDouble("lon"),
                    heading = if (obj.has("heading")) obj.getDouble("heading") else 0.0,
                    t = if (obj.has("t")) obj.getDouble("t") else 0.0,
                    isGnssHealthy = (status == "healthy" || status == "degraded"),
                    velocity = if (obj.has("velocity")) obj.getDouble("velocity") else 0.0,
                    uncertainty = if (obj.has("uncertainty")) obj.getDouble("uncertainty") else 0.0,
                    covXX = if (obj.has("cov_xx")) obj.getDouble("cov_xx") else 0.0,
                    covYY = if (obj.has("cov_yy")) obj.getDouble("cov_yy") else 0.0,
                    covXY = if (obj.has("cov_xy")) obj.getDouble("cov_xy") else 0.0,
                )
            )
        }
        return points
    }

    suspend fun startSimulation(speedMultiplier: Int = 1) {
        if (fusedData.isEmpty() || gnssData.isEmpty()) {
            loadData()
        }
        if (fusedData.isEmpty()) return

        _isRunning.value = true

        val maxPoints = minOf(fusedData.size, gnssData.size)
        
        // Emulate a 10Hz output, but speed it up if requested
        val delayMs = (100L / speedMultiplier).coerceAtLeast(10L)

        val currentFusedTrace = mutableListOf<TrajectoryPoint>()
        val currentGnssTrace = mutableListOf<TrajectoryPoint>()

        for (i in 0 until maxPoints) {
            if (!_isRunning.value) break

            val fPt = fusedData[i]
            val gPt = gnssData[i]

            _simulatedFusedPoint.value = fPt
            _simulatedGnssPoint.value = gPt

            currentFusedTrace.add(fPt)
            currentGnssTrace.add(gPt)

            // Update traces (copying list to trigger StateFlow emission)
            _simulatedFusedTrace.value = currentFusedTrace.toList()
            _simulatedGnssTrace.value = currentGnssTrace.toList()

            delay(delayMs)
        }

        _isRunning.value = false
    }

    fun stopSimulation() {
        _isRunning.value = false
        _simulatedFusedTrace.value = emptyList()
        _simulatedGnssTrace.value = emptyList()
        _simulatedFusedPoint.value = null
        _simulatedGnssPoint.value = null
    }
}
