package com.aeris.mobile.domain.playback

import com.aeris.mobile.domain.model.Correction
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint

/** Frames [start]..[end] (inclusive) drawn as one solid polyline in one colour. */
data class TrackSegment(val start: Int, val end: Int, val status: GnssStatus)

/**
 * Splits the fused path for drawing:
 * - at every correction: the step frame[i-1] -> frame[i] is NOT part of any segment (it is drawn dashed);
 * - optionally where the frame status changes (frame colouring); those segments share the boundary frame so the
 *   solid line stays continuous.
 */
object TrackSegments {

    fun build(points: List<TrajectoryPoint>, corrections: List<Correction>, splitOnStatus: Boolean): List<TrackSegment> {
        if (points.isEmpty()) return emptyList()
        val breaks = corrections.map { it.frameIndex }.filter { it in 1 until points.size }.toHashSet()
        val out = mutableListOf<TrackSegment>()
        var start = 0
        var status = points[0].status
        for (i in 1 until points.size) {
            when {
                i in breaks -> {
                    out.add(TrackSegment(start, i - 1, status))
                    start = i
                    status = points[i].status
                }
                splitOnStatus && points[i].status != status -> {
                    out.add(TrackSegment(start, i, status))
                    start = i
                    status = points[i].status
                }
            }
        }
        out.add(TrackSegment(start, points.size - 1, status))
        return out
    }
}
