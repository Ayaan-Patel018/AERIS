package com.aeris.mobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.aeris.mobile.ui.theme.Aeris

/**
 * Grouped map controls with shared outer 12 dp rounded corners and 1 dp inner dividers per M02 §3.
 */
@Composable
fun MapControlGroup(
    onZoomIn: () -> Unit,
    onZoomOut: () -> Unit,
    onToggleStyle: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Column(
        modifier = modifier
            .shadow(4.dp, RoundedCornerShape(12.dp), ambientColor = colors.ink.copy(alpha = 0.14f))
            .clip(RoundedCornerShape(12.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(12.dp))
            .width(44.dp)
    ) {
        // Zoom in button
        MapControlButton(
            icon = Icons.Default.Add,
            description = "Zoom in",
            onClick = onZoomIn
        )

        HorizontalDivider(thickness = 1.dp, color = colors.harbor)

        // Zoom out button (minus glyph)
        MapControlButton(
            description = "Zoom out",
            onClick = onZoomOut,
            customContent = {
                Box(
                    modifier = Modifier
                        .size(width = 12.dp, height = 2.dp)
                        .background(colors.ink)
                )
            }
        )

        HorizontalDivider(thickness = 1.dp, color = colors.harbor)

        // Style toggle button (Layers glyph)
        MapControlButton(
            description = "Toggle map layer style",
            onClick = onToggleStyle,
            customContent = {
                Column(
                    verticalArrangement = Arrangement.spacedBy(2.5.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box(modifier = Modifier.size(width = 14.dp, height = 2.dp).background(colors.ink))
                    Box(modifier = Modifier.size(width = 14.dp, height = 2.dp).background(colors.ink))
                    Box(modifier = Modifier.size(width = 14.dp, height = 2.dp).background(colors.ink))
                }
            }
        )
    }
}

@Composable
private fun MapControlButton(
    description: String,
    onClick: () -> Unit,
    icon: ImageVector? = null,
    customContent: (@Composable () -> Unit)? = null,
) {
    val colors = Aeris.colors
    Box(
        modifier = Modifier
            .size(44.dp)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics {
                contentDescription = description
                role = Role.Button
            },
        contentAlignment = Alignment.Center
    ) {
        if (customContent != null) {
            customContent()
        } else if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = colors.ink,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}
