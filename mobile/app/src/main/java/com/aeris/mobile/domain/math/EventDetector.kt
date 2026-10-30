package com.aeris.mobile.domain.math

import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Key events detected along a trajectory timeline.
 */
sealed interface TimelineEvent {
    val timestampSec: Double
    val pointIndex: Int

    data class OutageStart(
        override val timestampSec: Double,
        override val pointIndex: Int,
        val outageId: String,
    ) : TimelineEvent

    data class Reacquisition(
        override val timestampSec: Double,
        override val pointIndex: Int,
        val separationMeters: Double,
        val outageId: String,
    ) : TimelineEvent

    data class MaxUncertainty(
        override val timestampSec: Double,
        override val pointIndex: Int,
        val uncertaintyMeters: Double,
    ) : TimelineEvent
}

object EventDetector {

    private const val EARTH_RADIUS_METERS = 6371000.0

    /**
     * Computes Haversine distance in metres between two geographic points.
     */
    fun haversineDistanceMeters(
        lat1: Double, lon1: Double,
        lat2: Double, lon2: Double
    ): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2.0) * sin(dLat / 2.0) +
                cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
                sin(dLon / 2.0) * sin(dLon / 2.0)
        val c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
        return EARTH_RADIUS_METERS * c
    }

    /**
     * Derives all OutageWindows and TimelineEvents dynamically from status transitions in points.
     */
    fun detectOutagesAndEvents(
        points: List<TrajectoryPoint>,
        baselinePoints: List<TrajectoryPoint> = emptyList()
    ): Pair<List<OutageWindow>, List<TimelineEvent>> {
        if (points.isEmpty()) return Pair(emptyList(), emptyList())

        val outages = mutableListOf<OutageWindow>()
        val events = mutableListOf<TimelineEvent>()

        var inOutage = false
        var startIndex = 0
        var outageCounter = 1
        var maxUncertaintyInCurrent = 0.0
        var maxUncertaintyIndex = 0

        for (i in points.indices) {
            val pt = points[i]
            val isDenied = pt.status == GnssStatus.OUTAGE || pt.status == GnssStatus.DEGRADED

            val sigma = pt.sigma ?: 0.0
            if (isDenied && sigma > maxUncertaintyInCurrent) {
                maxUncertaintyInCurrent = sigma
                maxUncertaintyIndex = i
            }

            if (!inOutage && isDenied) {
                // Outage started
                inOutage = true
                startIndex = i
                val outageId = "outage-$outageCounter"
                events.add(TimelineEvent.OutageStart(pt.timestampSec, i, outageId))
                maxUncertaintyInCurrent = sigma
                maxUncertaintyIndex = i
            } else if (inOutage && !isDenied) {
                // Outage ended / Re-acquisition
                inOutage = false
                val outageId = "outage-$outageCounter"
                val startPt = points[startIndex]
                val endPt = points[i]
                val duration = (endPt.timestampSec - startPt.timestampSec).coerceAtLeast(0.0)

                // Calculate separation distance at reacquisition:
                // distance between AERIS dead reckoning estimate and the baseline/GNSS fix at this frame
                val separation = if (i < baselinePoints.size) {
                    val basePt = baselinePoints[i]
                    haversineDistanceMeters(pt.lat, pt.lon, basePt.lat, basePt.lon)
                } else {
                    maxUncertaintyInCurrent
                }

                outages.add(
                    OutageWindow(
                        id = outageId,
                        startIndex = startIndex,
                        endIndex = i,
                        startSec = startPt.timestampSec,
                        endSec = endPt.timestampSec,
                        durationSec = duration,
                        startPoint = startPt,
                        endPoint = endPt,
                        maxUncertaintyMeters = maxUncertaintyInCurrent
                    )
                )

                events.add(TimelineEvent.Reacquisition(endPt.timestampSec, i, separation, outageId))
                if (maxUncertaintyInCurrent > 0.0) {
                    events.add(
                        TimelineEvent.MaxUncertainty(
                            points[maxUncertaintyIndex].timestampSec,
                            maxUncertaintyIndex,
                            maxUncertaintyInCurrent
                        )
                    )
                }
                outageCounter++
            }
        }

        // Handle case where trajectory ends while still in an outage
        if (inOutage && startIndex < points.size) {
            val outageId = "outage-$outageCounter"
            val startPt = points[startIndex]
            val endPt = points.last()
            val duration = (endPt.timestampSec - startPt.timestampSec).coerceAtLeast(0.0)
            outages.add(
                OutageWindow(
                    id = outageId,
                    startIndex = startIndex,
                    endIndex = points.lastIndex,
                    startSec = startPt.timestampSec,
                    endSec = endPt.timestampSec,
                    durationSec = duration,
                    startPoint = startPt,
                    endPoint = endPt,
                    maxUncertaintyMeters = maxUncertaintyInCurrent
                )
            )
        }

        return Pair(outages, events)
    }
}
