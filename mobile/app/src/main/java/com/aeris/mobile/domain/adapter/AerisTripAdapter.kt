package com.aeris.mobile.domain.adapter

import com.aeris.mobile.domain.math.EventDetector
import com.aeris.mobile.domain.model.Correction
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.DriveMeta
import com.aeris.mobile.domain.model.DriveMetrics
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import org.json.JSONArray
import org.json.JSONObject

/**
 * Parser for the backend's aeris-trip/1 export (backend/export_vdr.py, spec in mobile/docs/aeris_trip_v1.md).
 *
 * Pure Kotlin: no Context, so it runs in JVM unit tests. [BundledTripLoader] reads the assets.
 * - Frames are used exactly as emitted (causal); `t_s` is absolute seconds, never normalised.
 * - GNSS fixes are matched to frames by `t_s`, never by index.
 * - Outage windows come from `outages[]` only (not inferred from frame status).
 * - No error is computed in the app: metrics come only from the scorer's metrics file.
 */
object AerisTripAdapter {

    const val SCHEMA = "aeris-trip/1"
    const val METRICS_SCHEMA = "aeris-metrics/1"
    const val METRICS_PROVENANCE = "scored against VBOX reference - development drive, in-sample"

    /** Frame status -> GnssStatus. Used for frame colouring only; outages come from outages[]. */
    fun statusOf(status: String?): GnssStatus = when (status) {
        "gnss" -> GnssStatus.HEALTHY
        "dr" -> GnssStatus.OUTAGE
        "warmup" -> GnssStatus.UNKNOWN
        else -> GnssStatus.UNKNOWN
    }

    fun parse(json: String): Drive {
        val root = JSONObject(json)
        val meta = root.getJSONObject("meta")
        require(meta.optString("schema") == SCHEMA) { "not an $SCHEMA file: schema=${meta.optString("schema")}" }
        require(meta.has("referenceUsed") && !meta.getBoolean("referenceUsed")) {
            "refusing a trip whose meta.referenceUsed is not false"
        }

        val rawCorrections = root.getJSONArray("corrections")
        val correctionTimes = DoubleArray(rawCorrections.length()) { rawCorrections.getJSONObject(it).getDouble("t_s") }

        // Frames -> points. Cumulative distance skips correction steps (a jump is not distance driven).
        val frames = root.getJSONArray("frames")
        val points = ArrayList<TrajectoryPoint>(frames.length())
        var cumDist = 0.0
        for (i in 0 until frames.length()) {
            val f = frames.getJSONObject(i)
            val t = f.getDouble("t_s")
            val lat = f.getDouble("lat")
            val lon = f.getDouble("lon")
            if (i > 0 && correctionTimes.none { kotlin.math.abs(it - t) < 1e-6 }) {
                val p = points[i - 1]
                cumDist += EventDetector.haversineDistanceMeters(p.lat, p.lon, lat, lon)
            }
            val cov = f.optJSONArray("cov_en_m2")
            val major = optDouble(f, "sigma_major_m")
            points.add(
                TrajectoryPoint(
                    lat = lat,
                    lon = lon,
                    headingDeg = optDouble(f, "bearing_deg"),
                    speedMps = optDouble(f, "speed_mps"),
                    timestampSec = t,
                    status = statusOf(f.optString("status")),
                    sigma = major,
                    covXX = cov?.let { optDouble(it, 0) },
                    covYY = cov?.let { optDouble(it, 1) },
                    covXY = cov?.let { optDouble(it, 2) },
                    distanceMeters = cumDist,
                    sigmaMajorM = major,
                    sigmaMinorM = optDouble(f, "sigma_minor_m"),
                    ellipseAngleDeg = optDouble(f, "ellipse_angle_deg"),
                    fixAgeS = optDouble(f, "fix_age_s"),
                    stationary = if (f.has("stationary") && !f.isNull("stationary")) f.getBoolean("stationary") else null,
                )
            )
        }

        val corrections = (0 until rawCorrections.length()).map { k ->
            val c = rawCorrections.getJSONObject(k)
            val from = c.getJSONArray("from")
            val to = c.getJSONArray("to")
            Correction(
                tSec = c.getDouble("t_s"),
                frameIndex = firstIndexAtOrAfter(points, c.getDouble("t_s")),
                fromLat = from.getDouble(0), fromLon = from.getDouble(1),
                toLat = to.getDouble(0), toLon = to.getDouble(1),
                jumpM = c.getDouble("jump_m"),
                cause = c.getString("cause"),
            )
        }

        val outages = parseOutages(root.getJSONArray("outages"), points)
        val baseline = parseGnss(root.getJSONArray("gnss"))

        val driveId = meta.getString("drive")
        val sigma = meta.optJSONObject("sigma")
        val driveMeta = DriveMeta(
            id = "Drive $driveId",
            name = driveId,
            durationSec = meta.getDouble("duration_s"),
            totalDistanceMeters = points.lastOrNull()?.distanceMeters ?: 0.0,
            outageCount = outages.size,
            referenceAvailable = false,
            metricsAvailable = false,
            filter = meta.optString("filter").ifEmpty { null },
            note = meta.optString("note").ifEmpty { null },
            schema = meta.optString("schema").ifEmpty { null },
            schemaStatus = meta.optString("schema_status").ifEmpty { null },
            gitCommit = meta.optString("git_commit").ifEmpty { null },
            sigmaCalibrated = if (sigma != null && sigma.has("calibrated")) sigma.getBoolean("calibrated") else null,
        )

        return Drive(
            meta = driveMeta,
            points = points,
            outages = outages,
            baselinePoints = baseline,
            referencePoints = emptyList(),
            metrics = null,
            corrections = corrections,
        )
    }

    /**
     * Metrics for the drive's first outage window, from the scorer's `<drive>_metrics.json` (aeris-metrics/1).
     * Returns null unless the file says the reference was used for scoring only.
     */
    fun parseMetrics(json: String): DriveMetrics? {
        val root = JSONObject(json)
        if (root.optString("schema") != METRICS_SCHEMA) return null
        if (root.optString("reference_role") != "scoring_only") return null
        val outs = root.optJSONArray("outages") ?: return null
        if (outs.length() == 0) return null
        val o = outs.getJSONObject(0)
        return DriveMetrics(
            maxDriftMeters = o.getDouble("max_err"),
            meanErrorMeters = o.getDouble("mean_err"),
            totalOutageDurationSec = o.getDouble("end_s") - o.getDouble("start_s"),
            provenance = METRICS_PROVENANCE,
            endErrorMeters = optDouble(o, "end_err"),
            pathRatio = optDouble(o, "path_ratio"),
            insideOneSigmaPct = optDouble(o, "inside"),
            inSample = if (root.has("in_sample")) root.getBoolean("in_sample") else null,
        )
    }

    /** Index of the latest GNSS fix with t <= [tSec] (match by time, never by index); -1 if none. */
    fun latestFixIndexAt(fixes: List<TrajectoryPoint>, tSec: Double): Int {
        var lo = 0
        var hi = fixes.size - 1
        var best = -1
        while (lo <= hi) {
            val mid = (lo + hi) ushr 1
            if (fixes[mid].timestampSec <= tSec) { best = mid; lo = mid + 1 } else hi = mid - 1
        }
        return best
    }

    /** First frame index with t >= [tSec] (points are time-ordered); points.size if none. */
    fun firstIndexAtOrAfter(points: List<TrajectoryPoint>, tSec: Double): Int {
        var lo = 0
        var hi = points.size
        while (lo < hi) {
            val mid = (lo + hi) ushr 1
            if (points[mid].timestampSec < tSec - 1e-6) lo = mid + 1 else hi = mid
        }
        return lo
    }

    private fun parseOutages(arr: JSONArray, points: List<TrajectoryPoint>): List<OutageWindow> {
        val out = mutableListOf<OutageWindow>()
        for (k in 0 until arr.length()) {
            val o = arr.getJSONObject(k)
            val start = o.getDouble("start_s")
            val end = o.getDouble("end_s")
            val startIdx = firstIndexAtOrAfter(points, start)
            val endIdx = firstIndexAtOrAfter(points, end + 1e-6) - 1          // last frame with t <= end
            if (startIdx >= points.size || endIdx < startIdx) continue
            out.add(
                OutageWindow(
                    id = "outage-${k + 1}",
                    startIndex = startIdx,
                    endIndex = endIdx,
                    startSec = start,
                    endSec = end,
                    durationSec = end - start,
                    startPoint = points[startIdx],
                    endPoint = points[endIdx],
                    maxUncertaintyMeters = (startIdx..endIdx).maxOf { points[it].sigmaMajorM ?: 0.0 },
                    kind = o.optString("kind").ifEmpty { null },
                    lastFixSec = optDouble(o, "last_fix_s"),
                    firstFixAfterSec = optDouble(o, "first_fix_after_s"),
                    withheldFixCount = if (o.has("withheld_fix_count")) o.getInt("withheld_fix_count") else null,
                )
            )
        }
        return out
    }

    private fun parseGnss(arr: JSONArray): List<TrajectoryPoint> = (0 until arr.length()).map { k ->
        val g = arr.getJSONObject(k)
        TrajectoryPoint(
            lat = g.getDouble("lat"),
            lon = g.getDouble("lon"),
            headingDeg = null,
            speedMps = null,
            timestampSec = g.getDouble("t_s"),
            status = GnssStatus.HEALTHY,
            sigma = optDouble(g, "accuracy_m"),   // the phone's own reported accuracy, m
            covXX = null,
            covYY = null,
            covXY = null,
        )
    }

    private fun optDouble(o: JSONObject, key: String): Double? =
        if (!o.has(key) || o.isNull(key)) null else o.getDouble(key)

    private fun optDouble(a: JSONArray, i: Int): Double? =
        if (i >= a.length() || a.isNull(i)) null else a.getDouble(i)
}
