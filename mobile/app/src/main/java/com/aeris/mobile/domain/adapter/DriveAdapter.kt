package com.aeris.mobile.domain.adapter

import android.content.Context
import com.aeris.mobile.domain.math.EventDetector
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.DriveMeta
import com.aeris.mobile.domain.model.DriveMetrics
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader

object DriveAdapter {

    /**
     * Loads and parses the bundled S3b drive data from app assets.
     */
    suspend fun loadBundledDrive(context: Context): Drive = withContext(Dispatchers.IO) {
        val metaJson = loadMetadataJson(context)
        val totalDurationMeta = metaJson?.optDouble("total_duration_s", 681.1) ?: 681.1
        val isNormalized = metaJson?.optBoolean("t_normalized", true) ?: true

        val rawFused = parseTrajectoryPoints(context, "fused_output.json", isNormalized, totalDurationMeta)
        val baselinePoints = try {
            parseTrajectoryPoints(context, "gnss_only.json", isNormalized, totalDurationMeta)
        } catch (e: Exception) {
            emptyList()
        }
        val referencePoints = try {
            parseTrajectoryPoints(context, "reference_trajectory.json", isNormalized, totalDurationMeta)
        } catch (e: Exception) {
            emptyList()
        }

        // Compute cumulative distance on fused points
        val fusedPoints = mutableListOf<TrajectoryPoint>()
        var cumDist = 0.0
        for (i in rawFused.indices) {
            val curr = rawFused[i]
            if (i > 0) {
                val prev = rawFused[i - 1]
                cumDist += EventDetector.haversineDistanceMeters(prev.lat, prev.lon, curr.lat, curr.lon)
            }
            fusedPoints.add(curr.copy(distanceMeters = cumDist))
        }

        // Detect dynamic outages and events from data
        val (outages, _) = EventDetector.detectOutagesAndEvents(fusedPoints, baselinePoints)

        val totalDurationSec = if (fusedPoints.isNotEmpty()) {
            fusedPoints.last().timestampSec - fusedPoints.first().timestampSec
        } else totalDurationMeta

        val totalDistanceM = if (fusedPoints.isNotEmpty()) fusedPoints.last().distanceMeters else 0.0

        val meta = parseMetadata(metaJson, totalDurationSec, totalDistanceM, outages.size, referencePoints.isNotEmpty())
        val metrics = calculateMetrics(fusedPoints, baselinePoints, referencePoints, outages)

        Drive(
            meta = meta,
            points = fusedPoints,
            outages = outages,
            baselinePoints = baselinePoints,
            referencePoints = referencePoints,
            metrics = metrics,
        )
    }

    private fun loadMetadataJson(context: Context): JSONObject? {
        return try {
            val inputStream = context.assets.open("metadata.json")
            val reader = BufferedReader(InputStreamReader(inputStream))
            val jsonString = reader.readText()
            reader.close()
            JSONObject(jsonString)
        } catch (e: Exception) {
            null
        }
    }

    private fun parseTrajectoryPoints(
        context: Context,
        filename: String,
        isNormalized: Boolean,
        totalDurationSec: Double
    ): List<TrajectoryPoint> {
        val list = mutableListOf<TrajectoryPoint>()
        val inputStream = context.assets.open(filename)
        val reader = BufferedReader(InputStreamReader(inputStream))
        val jsonString = reader.readText()
        reader.close()

        val jsonArray = JSONArray(jsonString)
        for (i in 0 until jsonArray.length()) {
            val obj = jsonArray.getJSONObject(i)
            val statusStr = if (obj.has("status")) obj.getString("status") else null
            val status = GnssStatus.fromString(statusStr)

            val heading = if (obj.has("heading") && !obj.isNull("heading")) obj.getDouble("heading") else null
            val speed = if (obj.has("velocity") && !obj.isNull("velocity")) obj.getDouble("velocity") else null
            val rawT = if (obj.has("t") && !obj.isNull("t")) obj.getDouble("t") else 0.0
            val tSec = if (isNormalized) rawT * totalDurationSec else rawT

            val sigma = if (obj.has("uncertainty") && !obj.isNull("uncertainty")) obj.getDouble("uncertainty") else null

            val covXX = if (obj.has("cov_xx") && !obj.isNull("cov_xx")) obj.getDouble("cov_xx") else null
            val covYY = if (obj.has("cov_yy") && !obj.isNull("cov_yy")) obj.getDouble("cov_yy") else null
            val covXY = if (obj.has("cov_xy") && !obj.isNull("cov_xy")) obj.getDouble("cov_xy") else null

            list.add(
                TrajectoryPoint(
                    lat = obj.getDouble("lat"),
                    lon = obj.getDouble("lon"),
                    headingDeg = heading,
                    speedMps = speed,
                    timestampSec = tSec,
                    status = status,
                    sigma = sigma,
                    covXX = covXX,
                    covYY = covYY,
                    covXY = covXY,
                    distanceMeters = 0.0 // updated with cumulative in loadBundledDrive
                )
            )
        }
        return list
    }

    private fun parseMetadata(
        obj: JSONObject?,
        computedDuration: Double,
        computedDistance: Double,
        outageCount: Int,
        hasReference: Boolean
    ): DriveMeta {
        if (obj == null) {
            return DriveMeta(
                id = "Drive S3b",
                name = "Warwick Campus Loop",
                durationSec = computedDuration,
                totalDistanceMeters = computedDistance,
                outageCount = outageCount,
                referenceAvailable = hasReference,
                metricsAvailable = false,
            )
        }

        val rawId = if (obj.has("drive_id")) obj.getString("drive_id") else "S3b"
        val driveId = if (rawId.startsWith("S3b")) "Drive S3b" else rawId
        val desc = if (obj.has("description")) obj.getString("description") else "Warwick Campus Loop"
        val dur = if (obj.has("total_duration_s")) obj.getDouble("total_duration_s") else computedDuration
        val dist = if (obj.has("total_distance_m")) obj.getDouble("total_distance_m") else computedDistance

        return DriveMeta(
            id = driveId,
            name = desc,
            durationSec = dur,
            totalDistanceMeters = dist,
            outageCount = outageCount,
            referenceAvailable = hasReference,
            metricsAvailable = true,
        )
    }

    private fun calculateMetrics(
        fused: List<TrajectoryPoint>,
        baseline: List<TrajectoryPoint>,
        reference: List<TrajectoryPoint>,
        outages: List<com.aeris.mobile.domain.model.OutageWindow>
    ): DriveMetrics? {
        val groundTruth = if (reference.isNotEmpty()) reference else baseline
        if (groundTruth.isEmpty() || fused.isEmpty()) return null

        var maxDrift = 0.0
        var errorSum = 0.0
        var count = 0

        val maxLen = minOf(fused.size, groundTruth.size)
        for (i in 0 until maxLen) {
            val f = fused[i]
            val g = groundTruth[i]
            if (f.status == GnssStatus.OUTAGE || f.status == GnssStatus.DEGRADED) {
                val err = EventDetector.haversineDistanceMeters(f.lat, f.lon, g.lat, g.lon)
                if (err > maxDrift) maxDrift = err
                errorSum += err
                count++
            }
        }

        val totalOutageDuration = outages.sumOf { it.durationSec }
        val meanError = if (count > 0) errorSum / count else 0.0

        return DriveMetrics(
            maxDriftMeters = maxDrift,
            meanErrorMeters = meanError,
            totalOutageDurationSec = totalOutageDuration,
            provenance = if (reference.isNotEmpty()) "reference_trajectory.json" else "gnss_only baseline comparison"
        )
    }
}
