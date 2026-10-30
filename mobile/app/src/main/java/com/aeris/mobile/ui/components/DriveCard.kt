package com.aeris.mobile.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters

/**
 * Drive card on Explore matching Mockup 00 Screen 1 & R3 § 5.
 *
 * 158 dp wide, 16 dp radius, route thumbnail (real path from data, outage dotted amber),
 * label, duration + distance, and satellite loss indicator.
 */
@Composable
fun DriveCard(
    drive: Drive,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    val durationMin = (drive.meta.durationSec / 60.0).toInt().coerceAtLeast(1)
    val distanceFormatted = Formatters.formatDistance(drive.meta.totalDistanceMeters)
    val outageCount = drive.outages.size

    val lossText = when {
        outageCount == 0 -> "No satellite loss"
        outageCount == 1 -> "1 satellite loss"
        else -> "$outageCount satellite losses"
    }

    Column(
        modifier = modifier
            .width(162.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .padding(12.dp)
            .semantics {
                role = Role.Button
                contentDescription = "${drive.meta.id}, $durationMin min, $distanceFormatted, $lossText"
            }
    ) {
        // Thumbnail: 138 x 64 dp canvas drawing real path
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(colors.chalk)
        ) {
            Canvas(modifier = Modifier.matchParentSize().padding(6.dp)) {
                val pts = drive.points
                if (pts.size >= 2) {
                    val minLat = pts.minOf { it.lat }
                    val maxLat = pts.maxOf { it.lat }
                    val minLon = pts.minOf { it.lon }
                    val maxLon = pts.maxOf { it.lon }

                    val latSpan = (maxLat - minLat).coerceAtLeast(1e-5)
                    val lonSpan = (maxLon - minLon).coerceAtLeast(1e-5)

                    fun norm(lat: Double, lon: Double): Offset {
                        val x = ((lon - minLon) / lonSpan * size.width).toFloat()
                        val y = ((maxLat - lat) / latSpan * size.height).toFloat()
                        return Offset(x, y)
                    }

                    // Draw healthy path segments in cobalt
                    val path = Path()
                    val outagePath = Path()

                    var pathStarted = false
                    var outageStarted = false

                    for (i in pts.indices) {
                        val pt = pts[i]
                        val offset = norm(pt.lat, pt.lon)
                        val isOutage = pt.status == GnssStatus.OUTAGE || pt.status == GnssStatus.DEGRADED

                        if (isOutage) {
                            if (!outageStarted) {
                                outagePath.moveTo(offset.x, offset.y)
                                outageStarted = true
                            } else {
                                outagePath.lineTo(offset.x, offset.y)
                            }
                        } else {
                            if (!pathStarted) {
                                path.moveTo(offset.x, offset.y)
                                pathStarted = true
                            } else {
                                path.lineTo(offset.x, offset.y)
                            }
                        }
                    }

                    drawPath(
                        path = path,
                        color = colors.cobalt,
                        style = Stroke(width = 2.5f)
                    )

                    drawPath(
                        path = outagePath,
                        color = colors.amberLine,
                        style = Stroke(
                            width = 2.5f,
                            pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                        )
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Title: Drive label
        Text(
            text = drive.meta.id,
            color = colors.ink,
            fontSize = 13.5.sp,
            fontWeight = FontWeight.SemiBold,
        )

        Spacer(modifier = Modifier.height(2.dp))

        // Subtitle: e.g. "11 min • 3.4 km"
        Text(
            text = "$durationMin min • $distanceFormatted",
            color = colors.ink2,
            fontSize = 11.5.sp,
            fontWeight = FontWeight.Normal,
        )

        Spacer(modifier = Modifier.height(2.dp))

        // Third line: Satellite loss indicator
        Text(
            text = lossText,
            color = if (outageCount > 0) colors.amberLine else colors.ink3,
            fontSize = 11.5.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}
