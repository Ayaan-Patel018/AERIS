package com.aeris.mobile.domain.adapter

import com.aeris.mobile.domain.math.EllipseMath
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.playback.DriveMoments
import com.aeris.mobile.domain.playback.PlaybackBanner
import com.aeris.mobile.domain.playback.TrackSegments
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * C2 M5 — the bundled aeris-trip/1 asset (S3b, outage 200-260 s) through AerisTripAdapter.
 * Assets are read from src/main/assets like MapStyleTest (Gradle runs unit tests in the app module directory).
 */
class AerisTripAdapterTest {

    companion object {
        private const val TRIP = "src/main/assets/S3b_aeris_trip_v1.json"
        private const val METRICS = "src/main/assets/S3b_metrics.json"

        private fun read(path: String): String {
            val f = File(path)
            assertTrue("asset should exist: ${f.absolutePath}", f.exists())
            return f.readText()
        }

        private val tripJson: String by lazy { read(TRIP) }
        private val raw: JSONObject by lazy { JSONObject(tripJson) }
        private val drive: Drive by lazy { AerisTripAdapter.parse(tripJson) }
    }

    // ── frame count ───────────────────────────────────────────────────────────
    @Test
    fun frameCountMatchesTheExport() {
        assertEquals(6812, drive.points.size)
        assertEquals(raw.getJSONArray("frames").length(), drive.points.size)
        assertEquals(69, drive.baselinePoints.size)
        assertEquals(47, drive.corrections.size)
        assertTrue(drive.referencePoints.isEmpty())
        assertEquals(raw.getJSONObject("meta").getDouble("duration_s"), drive.meta.durationSec, 1e-9)
        assertEquals(drive.points.last().timestampSec, drive.meta.durationSec, 1e-9)
    }

    @Test
    fun timeIsAbsoluteAndIncreasing() {
        assertEquals(0.101, drive.points.first().timestampSec, 1e-9)       // t_s used as-is, never normalised
        for (i in 1 until drive.points.size) {
            assertTrue("t not increasing at $i", drive.points[i].timestampSec > drive.points[i - 1].timestampSec)
        }
    }

    // ── no GNSS inside outages ────────────────────────────────────────────────
    @Test
    fun noGnssFixInsideAnOutage() {
        assertEquals(1, drive.outages.size)
        for (o in drive.outages) {
            val inside = drive.baselinePoints.filter { it.timestampSec >= o.startSec && it.timestampSec <= o.endSec }
            assertTrue("fixes inside ${o.startSec}-${o.endSec}: ${inside.map { it.timestampSec }}", inside.isEmpty())
        }
    }

    @Test
    fun noGnssStatusFrameInsideAnOutage() {
        val o = drive.outages.single()
        for (i in o.startIndex..o.endIndex) {
            assertTrue("frame $i is gnss inside the outage", drive.points[i].status != GnssStatus.HEALTHY)
        }
    }

    // ── matching by t_s ───────────────────────────────────────────────────────
    @Test
    fun gnssIsMatchedByTimeNotIndex() {
        val fixes = drive.baselinePoints
        assertEquals(0.0, fixes.first().timestampSec, 1e-9)                // first fix is before the first frame
        for ((i, p) in drive.points.withIndex()) {
            val k = AerisTripAdapter.latestFixIndexAt(fixes, p.timestampSec)
            assertTrue("frame $i has no fix at or before it", k >= 0)
            assertTrue(fixes[k].timestampSec <= p.timestampSec)
            if (k + 1 < fixes.size) assertTrue(fixes[k + 1].timestampSec > p.timestampSec)
        }
        // Inside the outage the latest fix is the last one before it (184.001 s), never a withheld one
        val o = drive.outages.single()
        val k = AerisTripAdapter.latestFixIndexAt(fixes, drive.points[o.endIndex].timestampSec)
        assertEquals(184.001, fixes[k].timestampSec, 1e-9)
        assertEquals(-1, AerisTripAdapter.latestFixIndexAt(fixes, -1.0))
    }

    // ── status mapping ────────────────────────────────────────────────────────
    @Test
    fun statusMapping() {
        assertEquals(GnssStatus.HEALTHY, AerisTripAdapter.statusOf("gnss"))
        assertEquals(GnssStatus.OUTAGE, AerisTripAdapter.statusOf("dr"))
        assertEquals(GnssStatus.UNKNOWN, AerisTripAdapter.statusOf("warmup"))
        assertEquals(GnssStatus.UNKNOWN, AerisTripAdapter.statusOf("healthy"))   // old vocabulary is not accepted
        assertEquals(GnssStatus.UNKNOWN, AerisTripAdapter.statusOf(null))
        assertEquals(1411, drive.points.count { it.status == GnssStatus.HEALTHY })
        assertEquals(5233, drive.points.count { it.status == GnssStatus.OUTAGE })
        assertEquals(168, drive.points.count { it.status == GnssStatus.UNKNOWN })
    }

    // ── OutageWindow indices (from outages[] by t_s, not from frame status) ───
    @Test
    fun outageWindowIndicesFoundByTime() {
        val o = drive.outages.single()
        assertEquals(200.0, o.startSec, 1e-9)
        assertEquals(260.0, o.endSec, 1e-9)
        assertEquals(60.0, o.durationSec, 1e-9)
        assertEquals(1999, o.startIndex)
        assertEquals(2555, o.endIndex)
        assertTrue(drive.points[o.startIndex].timestampSec >= 200.0)
        assertTrue(drive.points[o.startIndex - 1].timestampSec < 200.0)
        assertTrue(drive.points[o.endIndex].timestampSec <= 260.0)
        assertTrue(drive.points[o.endIndex + 1].timestampSec > 260.0)
        assertEquals("simulated", o.kind)
        assertEquals(184.001, o.lastFixSec!!, 1e-9)
        assertEquals(262.127, o.firstFixAfterSec!!, 1e-9)
        assertEquals(5, o.withheldFixCount)
    }

    // ── ellipse conversion ────────────────────────────────────────────────────
    private fun angleDiffModPi(a: Double, b: Double): Double {
        var d = (a - b) % PI
        if (d > PI / 2) d -= PI
        if (d < -PI / 2) d += PI
        return abs(d)
    }

    /** Export convention on a synthetic covariance: (90 - deg(0.5 atan2(2 en, ee - nn))) mod 180, clockwise from North. */
    private fun exportAngleDeg(ee: Double, nn: Double, en: Double): Double {
        val a = 90.0 - Math.toDegrees(0.5 * atan2(2 * en, ee - nn))
        return ((a % 180.0) + 180.0) % 180.0
    }

    @Test
    fun ellipseConversionOnSyntheticCovariances() {
        // (ee, nn, en) -> expected major-axis bearing
        val cases = listOf(
            Triple(1.0, 9.0, 0.0) to 0.0,     // North
            Triple(9.0, 1.0, 0.0) to 90.0,    // East
            Triple(5.0, 5.0, 4.0) to 45.0,    // North-East
            Triple(5.0, 5.0, -4.0) to 135.0,  // South-East / North-West
        )
        for ((cov, bearing) in cases) {
            val (ee, nn, en) = cov
            assertEquals(bearing, exportAngleDeg(ee, nn, en), 1e-9)
            val fromCov = EllipseMath.computeEllipse(0.0, 0.0, ee, nn, en)
            val fromExport = EllipseMath.fromExport(0.0, 0.0, 3.0, 1.0, bearing)
            assertTrue(angleDiffModPi(fromCov.orientationRad, fromExport.orientationRad) < 1e-9)
            assertEquals(fromCov.semiMajorMeters, fromExport.semiMajorMeters, 1e-9)
            assertEquals(fromCov.semiMinorMeters, fromExport.semiMinorMeters, 1e-9)
        }
        assertEquals(PI / 2, EllipseMath.orientationRadFromBearingDeg(0.0), 1e-12)    // North = +90 deg from East
        assertEquals(0.0, EllipseMath.orientationRadFromBearingDeg(90.0), 1e-12)      // East
    }

    @Test
    fun ellipseFieldsAgreeWithTheCovarianceOnEveryFrame() {
        var checkedAngle = 0
        for ((i, p) in drive.points.withIndex()) {
            val ee = p.covXX ?: continue
            val nn = p.covYY!!
            val en = p.covXY!!
            val fromCov = EllipseMath.computeEllipse(p.lat, p.lon, ee, nn, en)
            val fromExport = EllipseMath.fromExport(p.lat, p.lon, p.sigmaMajorM!!, p.sigmaMinorM!!, p.ellipseAngleDeg!!)
            assertEquals("major at $i", fromCov.semiMajorMeters, fromExport.semiMajorMeters, 0.03)
            assertEquals("minor at $i", fromCov.semiMinorMeters, fromExport.semiMinorMeters, 0.03)
            // the angle is only defined for a clearly non-circular ellipse
            if (p.sigmaMajorM!! - p.sigmaMinorM!! > 1.0) {
                assertTrue(
                    "angle at $i",
                    angleDiffModPi(fromCov.orientationRad, fromExport.orientationRad) < Math.toRadians(1.0)
                )
                checkedAngle++
            }
            assertEquals(p.sigma!!, p.sigmaMajorM!!, 0.0)
            assertTrue(p.ellipseAngleDeg!! >= 0.0 && p.ellipseAngleDeg!! < 180.0)
            assertTrue(sqrt(ee + nn) >= p.sigmaMajorM!! - 0.03)
        }
        assertTrue("angle checked on $checkedAngle frames", checkedAngle > 100)
    }

    // ── corrections / drawing helpers ─────────────────────────────────────────
    @Test
    fun correctionsLandOnFramesAndSplitThePath() {
        for (c in drive.corrections) {
            assertEquals(c.tSec, drive.points[c.frameIndex].timestampSec, 1e-9)
            assertTrue(c.jumpM > 5.0)
        }
        val replay = drive.corrections.single { it.cause == "replay" }
        assertEquals(159.47, replay.jumpM, 0.01)
        for (split in listOf(true, false)) {
            val segs = TrackSegments.build(drive.points, drive.corrections, splitOnStatus = split)
            assertEquals(0, segs.first().start)
            assertEquals(drive.points.lastIndex, segs.last().end)
            for (c in drive.corrections) {
                assertTrue(segs.none { it.start < c.frameIndex && it.end >= c.frameIndex })    // no solid line over a jump
            }
        }
    }

    @Test
    fun bannerText() {
        val o = drive.outages.single()
        val inside = drive.points[o.startIndex + 100]
        assertEquals(
            "GNSS withheld (simulated outage) - AERIS dead reckoning, last fix ${inside.fixAgeS!!.roundToInt()} s ago",
            PlaybackBanner.textFor(inside, o)
        )
        val fresh = drive.points.first { it.fixAgeS != null && it.fixAgeS!! <= 15.0 }
        assertNull(PlaybackBanner.textFor(fresh, null))
        val stale = drive.points.firstOrNull { it.fixAgeS != null && it.fixAgeS!! > 15.0 && it.timestampSec < o.startSec }
        if (stale != null) assertEquals("No GNSS fix - dead reckoning", PlaybackBanner.textFor(stale, null))
    }

    @Test
    fun momentsComeFromTheData() {
        val moments = DriveMoments.build(drive)
        val o = drive.outages.single()
        assertTrue(moments.any { it.tSec == o.startSec && it.index == o.startIndex })
        assertTrue(moments.any { it.tSec == 262.127 })
        val jump = DriveMoments.firstCorrectionAfter(drive, o)
        assertNotNull(jump)
        assertEquals(262.127, jump!!.tSec, 1e-9)
        assertEquals("gnss_rejoin", jump.cause)
    }

    // ── metrics provenance ────────────────────────────────────────────────────
    @Test
    fun metricsOnlyFromTheMetricsAssetWithProvenance() {
        assertNull(drive.metrics)                                          // the trip file alone carries no error numbers
        val m = AerisTripAdapter.parseMetrics(read(METRICS))
        assertNotNull(m)
        assertEquals("scored against VBOX reference - development drive, in-sample", m!!.provenance)
        assertEquals(true, m.inSample)
        assertEquals(66.4652, m.meanErrorMeters, 1e-9)
        assertEquals(165.5407, m.endErrorMeters!!, 1e-9)
        assertEquals(60.0, m.totalOutageDurationSec, 1e-9)
        // not "scoring_only" -> refused
        val bad = JSONObject(read(METRICS)).put("reference_role", "input").toString()
        assertNull(AerisTripAdapter.parseMetrics(bad))
    }

    @Test(expected = IllegalArgumentException::class)
    fun refusesATripThatUsedTheReference() {
        val o = JSONObject(tripJson)
        o.getJSONObject("meta").put("referenceUsed", true)
        AerisTripAdapter.parse(o.toString())
    }

    // ── no deleted asset name referenced anywhere ─────────────────────────────
    @Test
    fun noDeletedAssetIsBundledOrReferenced() {
        val deleted = listOf("fused_output.json", "gnss_only.json", "metadata.json", "reference_trajectory.json")
        for (name in deleted) assertFalse("$name is still bundled", File("src/main/assets/$name").exists())
        val hits = File("src/main").walkTopDown()
            .filter { it.isFile && it.extension in setOf("kt", "java", "xml", "kts", "json") && it.length() < 1_000_000 }
            .flatMap { f -> deleted.filter { f.readText().contains(it) }.map { "${f.path}: $it" } }
            .toList()
        assertTrue("references to deleted assets: $hits", hits.isEmpty())
    }
}
