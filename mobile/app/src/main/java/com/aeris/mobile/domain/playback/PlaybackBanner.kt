package com.aeris.mobile.domain.playback

import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import kotlin.math.roundToInt

/**
 * Banner text for the replay screen, keyed on the active outage window (outages[]) and the frame's fix_age_s.
 */
object PlaybackBanner {

    /** Outside an outage the banner appears only when the last phone fix is older than this (S3b fixes arrive ~every 9 s). */
    const val NO_FIX_BANNER_AFTER_S = 15.0

    fun textFor(point: TrajectoryPoint?, activeOutage: OutageWindow?): String? {
        val age = point?.fixAgeS
        if (activeOutage != null) {
            val n = age?.roundToInt()?.toString() ?: "—"
            return "GNSS withheld (simulated outage) - AERIS dead reckoning, last fix $n s ago"
        }
        if (age != null && age > NO_FIX_BANNER_AFTER_S) return "No GNSS fix - dead reckoning"
        return null
    }
}
