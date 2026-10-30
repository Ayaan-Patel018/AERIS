package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.expandHorizontally
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * The available Map styles for AERIS per R2 § 1 & § 2.
 */
enum class AerisMapStyle(
    val label: String,
    val mapboxUri: String,
    val emoji: String,
) {
    AERIS_NIGHT(
        label = "Night",
        mapboxUri = com.mapbox.maps.Style.DARK,
        emoji = "N",
    ),
    AERIS_DAY(
        label = "Day",
        mapboxUri = com.mapbox.maps.Style.LIGHT,
        emoji = "D",
    ),
    STANDARD(
        label = "Standard",
        mapboxUri = com.mapbox.maps.Style.MAPBOX_STREETS,
        emoji = "S",
    ),
    SHADOW(
        label = "Dark",
        mapboxUri = com.mapbox.maps.Style.DARK,
        emoji = "K",
    ),
    SATELLITE(
        label = "Satellite",
        mapboxUri = com.mapbox.maps.Style.STANDARD_SATELLITE,
        emoji = "Sat",
    ),
}

/**
 * Collapsible map-style switcher.
 */
@Composable
fun MapStyleSelector(
    selected: AerisMapStyle,
    onStyleSelected: (AerisMapStyle) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.End,
    ) {
        // Expanded chips
        AnimatedVisibility(
            visible = expanded,
            enter = expandHorizontally(
                expandFrom = Alignment.End,
                animationSpec = spring(stiffness = Spring.StiffnessMediumLow),
            ) + fadeIn(),
            exit = shrinkHorizontally(
                shrinkTowards = Alignment.End,
                animationSpec = spring(stiffness = Spring.StiffnessMediumLow),
            ) + fadeOut(),
        ) {
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(32.dp))
                    .background(Color(0x22FFFFFF))
                    .border(
                        width = 1.dp,
                        color = Color(0x33FFFFFF),
                        shape = RoundedCornerShape(32.dp),
                    )
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AerisMapStyle.entries.forEach { style ->
                    StyleChip(
                        style = style,
                        isSelected = style == selected,
                        onClick = {
                            onStyleSelected(style)
                            expanded = false
                        },
                    )
                }
            }
        }

        if (expanded) Spacer(modifier = Modifier.width(8.dp))

        // Toggle button
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(Color(0x22FFFFFF))
                .border(
                    width = 1.dp,
                    color = if (expanded) Color(0x66FFFFFF) else Color(0x33FFFFFF),
                    shape = CircleShape,
                )
                .clickable { expanded = !expanded },
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Default.Menu,
                contentDescription = "Map style",
                tint = if (expanded) Color.White else Color(0xCCFFFFFF),
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun StyleChip(
    style: AerisMapStyle,
    isSelected: Boolean,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(if (isSelected) Color(0x44FFFFFF) else Color.Transparent)
            .border(
                width = 1.dp,
                color = if (isSelected) Color(0x66FFFFFF) else Color.Transparent,
                shape = RoundedCornerShape(20.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = style.label,
            style = MaterialTheme.typography.labelSmall,
            color = if (isSelected) Color.White else Color(0xCCFFFFFF),
            fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
            fontSize = 11.sp,
        )
    }
}
