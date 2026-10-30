package com.aeris.mobile.ui.screen

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.draw.shadow
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
import com.aeris.mobile.ui.components.AerisBottomNav
import com.aeris.mobile.ui.components.AerisNavTab
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters

enum class TripFilter {
    ALL,
    WITH_SATELLITE_LOSS,
    RECORDED_ON_PHONE
}

/**
 * Trips Tab Screen matching R5 § 1.
 *
 * Dedicated collection screen for browsing recorded drives and field logs.
 * Includes top bar with search & overflow, filter chips, full-width trip cards
 * with 72x72 dp thumbnails, and honest status chips.
 */
@Composable
fun TripsScreen(
    drives: List<Drive>,
    onSelectDrive: (Drive) -> Unit,
    onOpenSearch: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenRecord: () -> Unit,
    onNavigateTab: (AerisNavTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors
    var activeFilter by remember { mutableStateOf(TripFilter.ALL) }
    var showOverflowMenu by remember { mutableStateOf(false) }

    val filteredDrives = remember(drives, activeFilter) {
        when (activeFilter) {
            TripFilter.ALL -> drives
            TripFilter.WITH_SATELLITE_LOSS -> drives.filter { it.outages.isNotEmpty() }
            TripFilter.RECORDED_ON_PHONE -> emptyList() // Phone recordings are unprocessed
        }
    }

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(bottom = 76.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // 1. Top Bar: Title "Trips", Search Icon, Overflow Menu per R5 § 1
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Trips",
                    color = colors.ink,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Search icon
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(colors.paper)
                            .border(1.dp, colors.harbor, CircleShape)
                            .clickable(role = Role.Button, onClick = onOpenSearch),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Search,
                            contentDescription = "Search drives and moments",
                            tint = colors.ink,
                            modifier = Modifier.size(20.dp)
                        )
                    }

                    // Overflow Menu
                    Box {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(colors.paper)
                                .border(1.dp, colors.harbor, CircleShape)
                                .clickable(role = Role.Button) { showOverflowMenu = true },
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.MoreVert,
                                contentDescription = "More options",
                                tint = colors.ink,
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        DropdownMenu(
                            expanded = showOverflowMenu,
                            onDismissRequest = { showOverflowMenu = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("Import a drive", color = colors.ink) },
                                onClick = { showOverflowMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Manage storage", color = colors.ink) },
                                onClick = { showOverflowMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Settings", color = colors.ink) },
                                onClick = {
                                    showOverflowMenu = false
                                    onOpenSettings()
                                }
                            )
                        }
                    }
                }
            }

            // 2. Filter Chips: All, With satellite loss, Recorded on this phone per R5 § 1
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 6.dp)
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TripScopeChip(
                    label = "All",
                    selected = activeFilter == TripFilter.ALL,
                    onClick = { activeFilter = TripFilter.ALL }
                )
                TripScopeChip(
                    label = "With satellite loss",
                    selected = activeFilter == TripFilter.WITH_SATELLITE_LOSS,
                    onClick = { activeFilter = TripFilter.WITH_SATELLITE_LOSS }
                )
                TripScopeChip(
                    label = "Recorded on this phone",
                    selected = activeFilter == TripFilter.RECORDED_ON_PHONE,
                    onClick = { activeFilter = TripFilter.RECORDED_ON_PHONE }
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 3. Section: From AERIS exports
            if (activeFilter != TripFilter.RECORDED_ON_PHONE) {
                Text(
                    text = "From AERIS exports",
                    color = colors.ink2,
                    fontSize = 13.5.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp)
                )

                filteredDrives.forEach { drive ->
                    TripRowCard(
                        drive = drive,
                        onClick = { onSelectDrive(drive) },
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp)
                    )
                }
            }

            // 4. Section: Recorded on this phone per R5 § 1
            if (activeFilter == TripFilter.ALL || activeFilter == TripFilter.RECORDED_ON_PHONE) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Recorded on this phone",
                    color = colors.ink2,
                    fontSize = 13.5.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp)
                )

                // Unprocessed phone recording card per R5 § 1 & R5 § 7
                UnprocessedTripRowCard(
                    title = "Trip 2026-10-18 17:42",
                    durationDistance = "4 min • 1.1 km",
                    onRecordNew = onOpenRecord,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp)
                )
            }
        }

        // Bottom Navigation Bar
        AerisBottomNav(
            selectedTab = AerisNavTab.TRIPS,
            onTabSelected = onNavigateTab,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

@Composable
private fun TripScopeChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = Aeris.colors
    Box(
        modifier = Modifier
            .height(34.dp)
            .clip(RoundedCornerShape(17.dp))
            .background(if (selected) colors.cobaltSoft else colors.paper)
            .border(
                width = if (selected) 1.5.dp else 1.dp,
                color = if (selected) colors.cobalt else colors.harbor,
                shape = RoundedCornerShape(17.dp)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = if (selected) colors.cobalt else colors.ink,
            fontSize = 13.sp,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
        )
    }
}

@Composable
private fun TripRowCard(
    drive: Drive,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors
    val durationMin = (drive.meta.durationSec / 60.0).toInt().coerceAtLeast(1)
    val distFormatted = Formatters.formatDistance(drive.meta.totalDistanceMeters)
    val outageCount = drive.outages.size

    val lossText = when {
        outageCount == 0 -> "No satellite loss"
        outageCount == 1 -> "1 satellite loss"
        else -> "$outageCount satellite losses"
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .padding(12.dp)
            .semantics {
                role = Role.Button
                contentDescription = "${drive.meta.id}, $durationMin min, $distFormatted, $lossText"
            },
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left 72x72 dp real route thumbnail per R5 § 1
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(RoundedCornerShape(12.dp))
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

                    val path = Path()
                    val outagePath = Path()

                    pts.forEachIndexed { i, p ->
                        val off = norm(p.lat, p.lon)
                        if (i == 0) {
                            path.moveTo(off.x, off.y)
                        } else {
                            if (p.status == GnssStatus.OUTAGE) {
                                outagePath.lineTo(off.x, off.y)
                            } else {
                                path.lineTo(off.x, off.y)
                                outagePath.moveTo(off.x, off.y)
                            }
                        }
                    }

                    drawPath(
                        path = path,
                        color = colors.cobalt,
                        style = Stroke(width = 3.dp.toPx())
                    )

                    drawPath(
                        path = outagePath,
                        color = colors.amberLine,
                        style = Stroke(
                            width = 3.dp.toPx(),
                            pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                        )
                    )
                }
            }
        }

        Spacer(modifier = Modifier.width(14.dp))

        // Right metadata column
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = drive.meta.id,
                color = colors.ink,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "$durationMin min • $distFormatted",
                color = colors.ink2,
                fontSize = 13.sp,
            )
            Spacer(modifier = Modifier.height(6.dp))

            // Status row: amber satellite loss icon or muted ink3
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (outageCount > 0) {
                    Box(
                        modifier = Modifier
                            .size(6.dp)
                            .clip(CircleShape)
                            .background(colors.amberLine)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = lossText,
                        color = colors.ink,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium
                    )
                } else {
                    Text(
                        text = "No satellite loss",
                        color = colors.ink3,
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun UnprocessedTripRowCard(
    title: String,
    durationDistance: String,
    onRecordNew: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left placeholder thumbnail
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(colors.chalk),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "RAW",
                color = colors.ink3,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.width(14.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = colors.ink,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = durationDistance,
                color = colors.ink2,
                fontSize = 12.5.sp,
            )
            Spacer(modifier = Modifier.height(6.dp))

            // Slate chip: "Recorded on this phone, not yet processed" per R5 § 1
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .background(colors.slate.copy(alpha = 0.12f))
                    .padding(horizontal = 8.dp, vertical = 3.dp)
            ) {
                Text(
                    text = "Recorded on this phone, not yet processed",
                    color = colors.slate,
                    fontSize = 10.5.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}
