package com.aeris.mobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.aeris.mobile.ui.theme.Aeris

/**
 * Clean floating Layers button matching Mockup 00 screens 1, 4, and 5.
 * Replaces the multi-button zoom clutter on mobile screens per R6 § 3.4.
 */
@Composable
fun LayersButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Box(
        modifier = modifier
            .size(44.dp)
            .shadow(4.dp, RoundedCornerShape(12.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
            .clip(RoundedCornerShape(12.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(12.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = "Map layers and style"
            },
        contentAlignment = Alignment.Center
    ) {
        // Authentic stacked map layers icon per V0 § 1 / V4 § 3
        androidx.compose.foundation.Canvas(modifier = Modifier.size(20.dp)) {
            val strokeW = 1.8.dp.toPx()
            val w = size.width
            val h = size.height
            val cx = w / 2f
            val leftX = w * 0.15f
            val rightX = w * 0.85f
            val topY = h * 0.18f
            val midY = h * 0.42f
            val botY = h * 0.64f
            val chevronOffset = h * 0.22f

            // Top rhombus layer
            val topPath = androidx.compose.ui.graphics.Path().apply {
                moveTo(cx, topY)
                lineTo(rightX, midY)
                lineTo(cx, botY)
                lineTo(leftX, midY)
                close()
            }
            drawPath(
                path = topPath,
                color = colors.ink,
                style = androidx.compose.ui.graphics.drawscope.Stroke(
                    width = strokeW,
                    cap = androidx.compose.ui.graphics.StrokeCap.Round,
                    join = androidx.compose.ui.graphics.StrokeJoin.Round
                )
            )

            // Lower chevron layer
            val lowerPath = androidx.compose.ui.graphics.Path().apply {
                moveTo(leftX, midY + chevronOffset)
                lineTo(cx, botY + chevronOffset)
                lineTo(rightX, midY + chevronOffset)
            }
            drawPath(
                path = lowerPath,
                color = colors.ink,
                style = androidx.compose.ui.graphics.drawscope.Stroke(
                    width = strokeW,
                    cap = androidx.compose.ui.graphics.StrokeCap.Round,
                    join = androidx.compose.ui.graphics.StrokeJoin.Round
                )
            )
        }
    }
}
