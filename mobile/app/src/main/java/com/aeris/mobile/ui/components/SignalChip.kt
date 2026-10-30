package com.aeris.mobile.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.core.source.SignalState
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters

/**
 * Universal Signal Chip anchoring satellite honesty across Explore, Navigating, and Playback per R1 § 4 & R3 § 3.
 */
@Composable
fun SignalChip(
    signalState: SignalState,
    modifier: Modifier = Modifier,
    elapsedLostSeconds: Double? = null,
) {
    if (signalState == SignalState.Unknown) return // Hidden when off per R3 § 3

    val colors = Aeris.colors

    val (bgColor, borderColor, dotColor, labelText) = when (signalState) {
        SignalState.Locked -> Quadruple(
            colors.paper,
            colors.harbor,
            colors.teal,
            "Satellite fix"
        )
        SignalState.Lost -> {
            val timeSuffix = if (elapsedLostSeconds != null && elapsedLostSeconds > 0) {
                " • ${Formatters.formatMmSs(elapsedLostSeconds)}"
            } else ""
            Quadruple(
                colors.amberSoft,
                colors.amber.copy(alpha = 0.5f),
                colors.amberLine,
                "Satellite signal lost$timeSuffix"
            )
        }
        SignalState.Searching -> Quadruple(
            colors.paper,
            colors.harbor,
            colors.slate,
            "Searching for satellites"
        )
        SignalState.Unknown -> Quadruple(
            colors.paper,
            colors.harbor,
            colors.slate,
            ""
        )
    }

    val animatedBg by animateColorAsState(targetValue = bgColor, label = "chipBg")
    val animatedBorder by animateColorAsState(targetValue = borderColor, label = "chipBorder")
    val animatedDot by animateColorAsState(targetValue = dotColor, label = "chipDot")

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
            .clip(RoundedCornerShape(32.dp))
            .background(animatedBg)
            .border(1.dp, animatedBorder, RoundedCornerShape(32.dp))
            .padding(horizontal = 14.dp, vertical = 7.dp)
            .semantics(mergeDescendants = true) {
                contentDescription = "GNSS Status: $labelText"
            }
    ) {
        // Status indicator dot
        Box(
            modifier = Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(animatedDot)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = labelText,
            color = colors.ink,
            fontSize = 12.5.sp,
            fontWeight = FontWeight.Medium,
            lineHeight = 15.sp,
        )
    }
}

/**
 * Backwards compatibility overload for legacy GnssSignalState
 */
enum class GnssSignalState {
    LOCKED,
    DEAD_RECKONING,
    DEGRADED,
    UNKNOWN,
}

@Composable
fun SignalChip(
    signalState: GnssSignalState,
    modifier: Modifier = Modifier,
    satelliteCount: Int? = null,
) {
    val mapped = when (signalState) {
        GnssSignalState.LOCKED -> SignalState.Locked
        GnssSignalState.DEAD_RECKONING, GnssSignalState.DEGRADED -> SignalState.Lost
        GnssSignalState.UNKNOWN -> SignalState.Unknown
    }
    SignalChip(signalState = mapped, modifier = modifier)
}

private data class Quadruple<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
