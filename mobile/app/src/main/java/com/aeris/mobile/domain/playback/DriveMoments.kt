package com.aeris.mobile.domain.playback

import com.aeris.mobile.domain.adapter.AerisTripAdapter
import com.aeris.mobile.domain.model.Correction
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.OutageWindow

enum class MomentKind { GNSS_WITHHELD, GNSS_BACK, CORRECTION }

/** A point of interest on the replay timeline, derived only from outages[] and corrections[]. */
data class Moment(
    val kind: MomentKind,
    val title: String,
    val tSec: Double,
    val index: Int,
    val detail: String,
    val outage: OutageWindow? = null,
)

object DriveMoments {

    /** Corrections at least this long become their own moment (same threshold as the map labels). */
    const val CORRECTION_MOMENT_MIN_M = 20.0

    fun build(drive: Drive): List<Moment> {
        val out = mutableListOf<Moment>()
        for (o in drive.outages) {
            val withheld = o.withheldFixCount?.let { ", $it fixes withheld" } ?: ""
            out.add(
                Moment(
                    MomentKind.GNSS_WITHHELD, "GNSS withheld", o.startSec, o.startIndex,
                    "${(o.endSec - o.startSec).toInt()} s ${o.kind ?: ""} outage$withheld".replace("  ", " "), o,
                )
            )
            val backT = o.firstFixAfterSec ?: o.endSec
            val backIdx = AerisTripAdapter.firstIndexAtOrAfter(drive.points, backT).coerceAtMost(drive.points.lastIndex)
            val jump = firstCorrectionAfter(drive, o)
            out.add(
                Moment(
                    MomentKind.GNSS_BACK, "GNSS back", backT, backIdx,
                    jump?.let { String.format(java.util.Locale.US, "AERIS jumped %.1f m at the new fix", it.jumpM) }
                        ?: "first fix after the outage",
                    o,
                )
            )
        }
        for (c in drive.corrections) {
            if (c.jumpM < CORRECTION_MOMENT_MIN_M) continue
            out.add(
                Moment(
                    MomentKind.CORRECTION, String.format(java.util.Locale.US, "Correction %.0f m", c.jumpM),
                    c.tSec, c.frameIndex, c.cause.replace('_', ' '),
                )
            )
        }
        return out.filter { it.index in drive.points.indices }.sortedBy { it.tSec }
    }

    /**
     * The correction at the first phone fix after the outage (else the first one after the window): the jump
     * "from the new fix". Null when there is none.
     */
    fun firstCorrectionAfter(drive: Drive, outage: OutageWindow): Correction? {
        val t0 = outage.firstFixAfterSec ?: outage.endSec
        return drive.corrections.firstOrNull { it.tSec >= t0 - 1e-6 }
    }

    /** Up to [limit] corrections after the outage window, in time order. */
    fun correctionsAfter(drive: Drive, outage: OutageWindow, limit: Int = 3): List<Correction> =
        drive.corrections.filter { it.tSec >= outage.endSec }.take(limit)
}
