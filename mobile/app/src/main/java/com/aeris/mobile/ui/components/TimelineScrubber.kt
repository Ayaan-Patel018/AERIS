package com.aeris.mobile.ui.components

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.ui.theme.Aeris

/**
 * High-precision interactive timeline scrubber with real data-derived outage bands per M07 §2.
 */
@Composable
fun TimelineScrubber(
    currentFraction: Float,
    durationSec: Double,
    outages: List<OutageWindow>,
    isPlaying: Boolean,
    speed: Float,
    onSeekFraction: (Float) -> Unit,
    onTogglePlayPause: () -> Unit,
    onCycleSpeed: () -> Unit,
    onJumpOutage: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors
    var isDragging by remember { mutableStateOf(false) }

    val trackHeight by animateDpAsState(
        targetValue = if (isDragging) 10.dp else 6.dp,
        label = "trackHeight"
    )

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        // Upper row: Interactive Canvas Track with Outage Bands & Thumb
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .pointerInput(durationSec) {
                    detectTapGestures { offset ->
                        val fraction = (offset.x / size.width).coerceIn(0f, 1f)
                        onSeekFraction(fraction)
                    }
                }
                .pointerInput(durationSec) {
                    detectDragGestures(
                        onDragStart = { isDragging = true },
                        onDragEnd = { isDragging = false },
                        onDragCancel = { isDragging = false }
                    ) { change, _ ->
                        change.consume()
                        val fraction = (change.position.x / size.width).coerceIn(0f, 1f)
                        onSeekFraction(fraction)
                    }
                }
                .semantics {
                    progressBarRangeInfo = ProgressBarRangeInfo(currentFraction, 0f..1f)
                    contentDescription = "Timeline scrubber"
                },
            contentAlignment = Alignment.CenterStart
        ) {
            Canvas(modifier = Modifier.fillMaxWidth().height(trackHeight)) {
                val canvasWidth = size.width
                val canvasHeight = size.height

                // Base track
                drawRoundRect(
                    color = colors.harbor,
                    topLeft = Offset(0f, 0f),
                    size = Size(canvasWidth, canvasHeight),
                    cornerRadius = CornerRadius(canvasHeight / 2, canvasHeight / 2)
                )

                // Render dynamic outage bands
                if (durationSec > 0.0) {
                    for (outage in outages) {
                        val startFrac = (outage.startSec / durationSec).toFloat().coerceIn(0f, 1f)
                        val endFrac = (outage.endSec / durationSec).toFloat().coerceIn(0f, 1f)
                        val bandX = startFrac * canvasWidth
                        val bandW = (endFrac - startFrac) * canvasWidth

                        drawRoundRect(
                            color = colors.amberSoft,
                            topLeft = Offset(bandX, 0f),
                            size = Size(bandW, canvasHeight),
                            cornerRadius = CornerRadius(2f, 2f)
                        )
                        // Accent line for outage band
                        drawRect(
                            color = colors.amber,
                            topLeft = Offset(bandX, 0f),
                            size = Size(bandW, 1.5.dp.toPx())
                        )
                    }
                }

                // Progress track (travelled)
                val progressWidth = (canvasWidth * currentFraction).coerceIn(0f, canvasWidth)
                drawRoundRect(
                    color = colors.cobalt,
                    topLeft = Offset(0f, 0f),
                    size = Size(progressWidth, canvasHeight),
                    cornerRadius = CornerRadius(canvasHeight / 2, canvasHeight / 2)
                )

                // Thumb circle
                val thumbRadius = if (isDragging) 9.dp.toPx() else 7.dp.toPx()
                drawCircle(
                    color = colors.paper,
                    radius = thumbRadius,
                    center = Offset(progressWidth, canvasHeight / 2)
                )
                drawCircle(
                    color = colors.cobalt,
                    radius = thumbRadius,
                    center = Offset(progressWidth, canvasHeight / 2),
                    style = androidx.compose.ui.graphics.drawscope.Stroke(width = 2.dp.toPx())
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Lower row: Play/Pause button | Current Time | Jump to Outage | Speed selector
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Play/Pause button
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(colors.ink)
                        .clickable(role = Role.Button, onClick = onTogglePlayPause)
                        .semantics {
                            role = Role.Button
                            contentDescription = if (isPlaying) "Pause replay" else "Play replay"
                        },
                    contentAlignment = Alignment.Center
                ) {
                    if (isPlaying) {
                        // Pause icon (two bars)
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                            Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                        }
                    } else {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = colors.paper,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                val currentSec = (currentFraction * durationSec).toInt()
                val totalSec = durationSec.toInt()
                Text(
                    text = String.format("%02d:%02d / %02d:%02d", currentSec / 60, currentSec % 60, totalSec / 60, totalSec % 60),
                    color = colors.ink,
                    fontSize = 13.5.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }

            // Right side: Jump to outage button & Speed selector
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (outages.isNotEmpty()) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(colors.amberSoft)
                            .border(1.dp, colors.amber.copy(alpha = 0.4f), RoundedCornerShape(8.dp))
                            .clickable(onClick = onJumpOutage)
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = "Jump outage",
                            color = colors.ink,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                // Speed chip
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .background(colors.harbor2)
                        .border(1.dp, colors.harbor, RoundedCornerShape(8.dp))
                        .clickable(onClick = onCycleSpeed)
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = "${speed}×",
                        color = colors.ink,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}
