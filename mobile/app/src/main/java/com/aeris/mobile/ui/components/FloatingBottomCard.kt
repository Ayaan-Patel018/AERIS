package com.aeris.mobile.ui.components

import androidx.compose.foundation.background
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import com.aeris.mobile.ui.theme.AerisBlack
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey15
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70
import com.aeris.mobile.ui.theme.AerisWhite

class WavyShape(
    private val cornerRadius: Dp = 32.dp,
    private val dipHeight: Dp = 16.dp
) : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val radius = with(density) { cornerRadius.toPx() }
        val dip = with(density) { dipHeight.toPx() }

        val path = Path().apply {
            moveTo(0f, radius)
            quadraticBezierTo(0f, 0f, radius, 0f)

            val midX = size.width / 2
            cubicTo(
                size.width * 0.2f, 0f,
                size.width * 0.3f, dip,
                midX, dip
            )
            cubicTo(
                size.width * 0.7f, dip,
                size.width * 0.8f, 0f,
                size.width - radius, 0f
            )

            quadraticBezierTo(size.width, 0f, size.width, radius)
            lineTo(size.width, size.height - radius)
            quadraticBezierTo(size.width, size.height, size.width - radius, size.height)
            lineTo(radius, size.height)
            quadraticBezierTo(0f, size.height, 0f, size.height - radius)
            close()
        }
        return Outline.Generic(path)
    }
}

@Composable
fun FloatingBottomCard(
    stateLabel: String,
    confidence: Int,
    distanceToDestination: String,
    eta: String,
    isGnssLocked: Boolean,
    onStopTracking: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(WavyShape())
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 24.dp, vertical = 24.dp)
            .padding(top = 16.dp) // Extra padding for the dip
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = if (isGnssLocked) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stateLabel,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.Medium
                )
            }
            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "Tracking Data",
                style = MaterialTheme.typography.displayMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "${confidence}% Confidence",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(modifier = Modifier.width(16.dp))
                Text(
                    text = "$eta ETA",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Swipe to stop",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                
                IconButton(
                    onClick = onStopTracking,
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.onSurface)
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowForward,
                        contentDescription = "Stop",
                        tint = MaterialTheme.colorScheme.surface
                    )
                }
            }
        }
    }
}
