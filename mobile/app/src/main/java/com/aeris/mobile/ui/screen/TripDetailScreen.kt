package com.aeris.mobile.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.playback.DriveMoments
import com.aeris.mobile.domain.playback.MomentKind
import com.aeris.mobile.ui.components.AerisBottomNav
import com.aeris.mobile.ui.components.AerisNavTab
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.MapView
import com.mapbox.maps.plugin.annotation.annotations
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.createPolylineAnnotationManager
import com.mapbox.maps.plugin.scalebar.scalebar

/**
 * Trip Detail Screen matching Mockup 00 Screen 6 & R5 § 2.
 *
 * Full route preview with amber outage segments, 3-column facts row,
 * Play Trip & Share actions, and Moments list.
 */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun TripDetailScreen(
    drive: Drive,
    onPlayTrip: () -> Unit,
    onPlayAtTimestamp: (Double) -> Unit = {},
    onBack: () -> Unit,
    onNavigateTab: (AerisNavTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    val durationMin = (drive.meta.durationSec / 60.0).toInt().coerceAtLeast(1)
    val distFormatted = Formatters.formatDistance(drive.meta.totalDistanceMeters)
    val outageCount = drive.outages.size
    var compareOutage by remember { mutableStateOf<com.aeris.mobile.domain.model.OutageWindow?>(null) }

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        // 1. Full-bleed Map View showing entire drive route
        TripDetailMapView(drive = drive)

        // 2. Top-left back button
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .statusBarsPadding()
                .padding(start = 16.dp, top = 8.dp)
                .size(40.dp)
                .clip(CircleShape)
                .background(colors.paper)
                .border(1.dp, colors.harbor, CircleShape)
                .clickable(role = Role.Button, onClick = onBack),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = "Back",
                tint = colors.ink,
                modifier = Modifier.size(20.dp)
            )
        }

        // 3. Bottom Trip Details Sheet per Mockup Screen 6 & R5 § 2
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(bottom = 76.dp) // space for bottom nav
                .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .padding(horizontal = 20.dp, vertical = 18.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Drag handle
            Box(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .width(36.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(colors.harbor)
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Title and Subtitle
            Text(
                text = drive.meta.id,
                color = colors.ink,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "Exported drive • AERIS track",
                color = colors.ink2,
                fontSize = 13.5.sp,
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Three-column Facts Row separated by vertical dividers per R5 § 2
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.chalk)
                    .padding(vertical = 14.dp, horizontal = 12.dp),
                horizontalArrangement = Arrangement.SpaceAround,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Distance column
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = distFormatted,
                        color = colors.ink,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "Distance",
                        color = colors.ink3,
                        fontSize = 11.5.sp,
                    )
                }

                Box(modifier = Modifier.size(width = 1.dp, height = 28.dp).background(colors.harbor))

                // Duration column
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$durationMin min",
                        color = colors.ink,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "Duration",
                        color = colors.ink3,
                        fontSize = 11.5.sp,
                    )
                }

                Box(modifier = Modifier.size(width = 1.dp, height = 28.dp).background(colors.harbor))

                // Satellite loss column
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$outageCount",
                        color = if (outageCount > 0) colors.amberLine else colors.ink,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "Satellite loss",
                        color = colors.ink3,
                        fontSize = 11.5.sp,
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons: Play Trip & Share
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = onPlayTrip,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colors.ink,
                        contentColor = colors.paper
                    ),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .weight(1.8f)
                        .height(50.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Play trip",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                OutlinedButton(
                    onClick = { /* Share */ },
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = colors.ink
                    ),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .weight(1f)
                        .height(50.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Share,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Share",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Moments Section per Mockup Screen 6 & R5 § 2
            Text(
                text = "Moments",
                color = colors.ink,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Moments from outages[] and corrections[] (tap opens playback 3 s before)
            val moments = remember(drive) { DriveMoments.build(drive) }
            if (moments.isEmpty()) {
                Text(text = "—", color = colors.ink2, fontSize = 12.sp)
            }
            moments.forEachIndexed { k, m ->
                if (k > 0) {
                    HorizontalDivider(thickness = 0.5.dp, color = colors.harbor, modifier = Modifier.padding(vertical = 8.dp))
                }
                MomentListRow(
                    iconText = when (m.kind) {
                        MomentKind.GNSS_WITHHELD -> "∿"
                        MomentKind.GNSS_BACK -> "✓"
                        MomentKind.CORRECTION -> "↯"
                    },
                    iconBg = if (m.kind == MomentKind.GNSS_BACK) colors.tealSoft else colors.amberSoft,
                    iconTint = if (m.kind == MomentKind.GNSS_BACK) colors.teal else colors.amberLine,
                    title = m.title,
                    subtitle = "${Formatters.formatMmSs(m.tSec)} • ${m.detail}",
                    onClick = { onPlayAtTimestamp((m.tSec - 3.0).coerceAtLeast(0.0)) }
                )
            }

            // Section 5: Scored numbers, only from the metrics asset (VBOX used for scoring only)
            Spacer(modifier = Modifier.height(20.dp))
            Text(
                text = "How AERIS did",
                color = colors.ink,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.chalk)
                    .border(1.dp, colors.harbor, RoundedCornerShape(12.dp))
                    .padding(14.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Scored against reference",
                            color = colors.ink,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                        if (drive.metrics?.inSample == true) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(colors.amberSoft)
                                    .padding(horizontal = 8.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    text = "Development drive, in-sample",
                                    color = colors.amberLine,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    val m = drive.metrics
                    Text(
                        text = if (m == null) "—" else String.format(
                            java.util.Locale.US,
                            "Outage window: mean error %.1f m • end error %s • max %.1f m • path ratio %s • inside 1σ %s (a calibrated 1σ would hold ~39 %%).",
                            m.meanErrorMeters,
                            m.endErrorMeters?.let { String.format(java.util.Locale.US, "%.1f m", it) } ?: "—",
                            m.maxDriftMeters,
                            m.pathRatio?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "—",
                            m.insideOneSigmaPct?.let { String.format(java.util.Locale.US, "%.1f %%", it) } ?: "—"
                        ),
                        color = colors.ink2,
                        fontSize = 12.5.sp,
                        lineHeight = 17.sp
                    )
                    if (m != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = m.provenance,
                            color = colors.ink3,
                            fontSize = 11.sp
                        )
                    }
                }
            }

            // Section 6: If we hadn't tracked per R5 § 2 & R5 § 6
            if (drive.outages.isNotEmpty()) {
                Spacer(modifier = Modifier.height(18.dp))
                Text(
                    text = "If we hadn't tracked",
                    color = colors.ink,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, RoundedCornerShape(12.dp))
                        .clickable { compareOutage = drive.outages.firstOrNull() }
                        .padding(14.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            val firstOutage = drive.outages.first()
                            val jump = DriveMoments.firstCorrectionAfter(drive, firstOutage)
                            Text(
                                text = "GNSS outage at ${Formatters.formatMmSs(firstOutage.startSec)}",
                                color = colors.ink,
                                fontSize = 13.5.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = jump?.let {
                                    String.format(java.util.Locale.US, "AERIS jumped %.1f m at the first fix after it.", it.jumpM)
                                } ?: "—",
                                color = colors.ink2,
                                fontSize = 12.sp
                            )
                        }
                        Text(
                            text = "View",
                            color = colors.cobalt,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            // Section 7: How this track was computed per R5 § 2 & M06 § 5
            Spacer(modifier = Modifier.height(18.dp))
            Text(
                text = "How this track was computed",
                color = colors.ink,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.chalk)
                    .border(1.dp, colors.harbor, RoundedCornerShape(12.dp))
                    .padding(14.dp)
            ) {
                Text(
                    text = "Filter: ${drive.meta.filter ?: "—"} (${drive.meta.schema ?: "—"} ${drive.meta.schemaStatus ?: ""} export, " +
                        "backend commit ${drive.meta.gitCommit?.take(7) ?: "—"}). Inputs: phone IMU and the phone's own GNSS fixes; " +
                        "no reference data used as input. ${drive.meta.note ?: ""}",
                    color = colors.ink2,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }
        }

        // Compare Sheet if opened
        if (compareOutage != null) {
            com.aeris.mobile.ui.sheet.CompareSheet(
                outage = compareOutage,
                drive = drive,
                onPlayMoment = { t ->
                    compareOutage = null
                    onPlayAtTimestamp(t)
                },
                onDismiss = { compareOutage = null }
            )
        }

        // 4. Bottom Navigation Bar
        AerisBottomNav(
            selectedTab = AerisNavTab.TRIPS,
            onTabSelected = onNavigateTab,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

@Composable
private fun MomentListRow(
    iconText: String,
    iconBg: androidx.compose.ui.graphics.Color,
    iconTint: androidx.compose.ui.graphics.Color,
    title: String,
    subtitle: String,
    onClick: () -> Unit = {},
) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onClick)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(iconBg),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = iconText,
                color = iconTint,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.width(14.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = colors.ink,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(1.dp))
            Text(
                text = subtitle,
                color = colors.ink2,
                fontSize = 12.sp,
            )
        }
    }
}

@Composable
private fun TripDetailMapView(drive: Drive) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    var cameraCentered by remember { mutableStateOf(false) }
    var styleLoaded by remember { mutableStateOf(false) }

    val polyManager = remember { mutableStateOf<PolylineAnnotationManager?>(null) }
    val routeAnno = remember { mutableStateOf<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation?>(null) }

    DisposableEffect(Unit) {
        onDispose {
            mapView.onStop()
            mapView.onDestroy()
        }
    }

    AndroidView(
        factory = {
            mapView.apply {
                scalebar.enabled = false
            }
        },
        update = { mv ->
            if (!styleLoaded) {
                mv.mapboxMap.loadStyleUri(com.mapbox.maps.Style.DARK)
                styleLoaded = true
            }

            val firstPt = drive.points.firstOrNull() ?: return@AndroidView

            if (!cameraCentered) {
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(Point.fromLngLat(firstPt.lon, firstPt.lat))
                        .zoom(15.2)
                        .pitch(0.0)
                        .bearing(0.0)
                        .build()
                )
                cameraCentered = true
            }

            if (polyManager.value == null) {
                polyManager.value = mv.annotations.createPolylineAnnotationManager()
            }

            val pm = polyManager.value ?: return@AndroidView

            if (routeAnno.value == null && drive.points.size >= 2) {
                val pts = drive.points.map { Point.fromLngLat(it.lon, it.lat) }
                routeAnno.value = pm.create(
                    PolylineAnnotationOptions()
                        .withPoints(pts)
                        .withLineColor("#6D8BFF")
                        .withLineWidth(4.0)
                        .withLineOpacity(0.9)
                )
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
