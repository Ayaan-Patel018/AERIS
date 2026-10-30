package com.aeris.mobile.ui.screen

import android.content.Context
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.aeris.mobile.core.source.PhoneGnssSource
import com.aeris.mobile.core.source.PositionState
import com.aeris.mobile.core.source.SignalState
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.DriveMeta
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.components.AerisBottomNav
import com.aeris.mobile.ui.components.AerisMapStyle
import com.aeris.mobile.ui.components.AerisNavTab
import com.aeris.mobile.ui.components.DriveCard
import com.aeris.mobile.ui.components.LayersButton
import com.aeris.mobile.ui.components.SearchPill
import com.aeris.mobile.ui.components.SignalChip
import com.aeris.mobile.ui.theme.Aeris
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.MapView
import com.mapbox.maps.plugin.annotation.annotations
import com.mapbox.maps.plugin.annotation.generated.PointAnnotation
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.createPointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.createPolylineAnnotationManager
import com.mapbox.maps.plugin.scalebar.scalebar

/**
 * Explore Home Screen matching Mockup 00 Screen 1 & R3 § 1.
 *
 * Full-bleed map, SearchPill, Filter chips, honest SignalChip, Locate button,
 * and Recent Drives peek sheet.
 */
@Composable
fun ExploreScreen(
    bundledDrive: Drive,
    isNightTheme: Boolean,
    onOpenSearch: () -> Unit,
    onOpenSettings: () -> Unit,
    onSelectDrive: (Drive) -> Unit,
    onNavigateTab: (AerisNavTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = Aeris.colors

    // Initialize Phone GNSS Source per R3 § 3
    val gnssSource = remember { PhoneGnssSource(context) }
    val positionState by gnssSource.state.collectAsState()

    DisposableEffect(Unit) {
        gnssSource.start()
        onDispose { gnssSource.stop() }
    }

    var selectedMapStyle by remember {
        mutableStateOf(if (isNightTheme) AerisMapStyle.AERIS_NIGHT else AerisMapStyle.AERIS_DAY)
    }

    LaunchedEffect(isNightTheme) {
        selectedMapStyle = if (isNightTheme) AerisMapStyle.AERIS_NIGHT else AerisMapStyle.AERIS_DAY
    }

    var selectedFilter by remember { mutableStateOf("Drives") }

    var zoomTrigger by remember { mutableStateOf(0) }
    var zoomOutTrigger by remember { mutableStateOf(0) }
    var locateTrigger by remember { mutableStateOf(0) }

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        // 1. Full-bleed Explore Map
        ExploreMapView(
            positionState = positionState,
            mapStyle = selectedMapStyle,
            bundledDrive = bundledDrive,
            showDrivePaths = selectedFilter == "Drives",
            zoomTrigger = zoomTrigger,
            zoomOutTrigger = zoomOutTrigger,
            locateTrigger = locateTrigger
        )

        // 2. Top UI with gradient scrim per V0 § 1 / V1 § 6
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .background(
                    androidx.compose.ui.graphics.Brush.verticalGradient(
                        colors = listOf(
                            colors.chalk.copy(alpha = 0.96f),
                            colors.chalk.copy(alpha = 0.88f),
                            colors.chalk.copy(alpha = 0.0f)
                        )
                    )
                )
                .statusBarsPadding()
                .padding(bottom = 12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                SearchPill(
                    onSearchClick = onOpenSearch,
                    onSettingsClick = onOpenSettings,
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Horizontally scrolling filter chips row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    listOf("Drives", "Saved", "Fuel", "Recent").forEach { label ->
                        val isSelected = label == selectedFilter
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .background(if (isSelected) colors.cobaltSoft else colors.paper)
                                .border(
                                    1.dp,
                                    if (isSelected) colors.cobalt else colors.harbor,
                                    RoundedCornerShape(20.dp)
                                )
                                .clickable { selectedFilter = if (isSelected) "" else label }
                                .padding(horizontal = 14.dp, vertical = 7.dp)
                        ) {
                            Text(
                                text = label,
                                color = if (isSelected) colors.cobalt else colors.ink,
                                fontSize = 12.5.sp,
                                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Row for SignalChip and LayersButton
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val sig = positionState?.signal ?: SignalState.Searching
                    SignalChip(signalState = sig)

                    LayersButton(
                        onClick = {
                            selectedMapStyle = if (selectedMapStyle == AerisMapStyle.AERIS_NIGHT) {
                                AerisMapStyle.AERIS_DAY
                            } else {
                                AerisMapStyle.AERIS_NIGHT
                            }
                        }
                    )
                }
            }
        }

        // 3. Floating Zoom Controls (+ / -) per V0 § 2 / R6 § 3.4 override
        Column(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = 328.dp)
                .width(44.dp)
                .shadow(4.dp, RoundedCornerShape(14.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
                .clip(RoundedCornerShape(14.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(14.dp)),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clickable(role = Role.Button) { zoomTrigger++ }
                    .semantics {
                        role = Role.Button
                        contentDescription = "Zoom in"
                    },
                contentAlignment = Alignment.Center
            ) {
                Text(text = "+", color = colors.ink, fontSize = 22.sp, fontWeight = FontWeight.Bold)
            }

            Box(
                modifier = Modifier
                    .width(32.dp)
                    .height(1.dp)
                    .background(colors.harbor)
            )

            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clickable(role = Role.Button) { zoomOutTrigger++ }
                    .semantics {
                        role = Role.Button
                        contentDescription = "Zoom out"
                    },
                contentAlignment = Alignment.Center
            ) {
                Text(text = "−", color = colors.ink, fontSize = 22.sp, fontWeight = FontWeight.Bold)
            }
        }

        // 4. Floating Locate Button
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = 270.dp)
                .size(44.dp)
                .shadow(4.dp, CircleShape, ambientColor = colors.ink.copy(alpha = 0.15f))
                .clip(CircleShape)
                .background(colors.paper)
                .border(1.dp, colors.harbor, CircleShape)
                .clickable(role = Role.Button) {
                    gnssSource.stop()
                    gnssSource.start()
                    locateTrigger++
                }
                .semantics {
                    role = Role.Button
                    contentDescription = "Center on my location"
                },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.LocationOn,
                contentDescription = null,
                tint = colors.ink,
                modifier = Modifier.size(20.dp)
            )
        }

        // 4. Bottom Peek Sheet: "Recent drives" cards
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(bottom = 76.dp) // space for bottom nav
                .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp), ambientColor = colors.ink.copy(alpha = 0.12f))
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .padding(top = 16.dp, bottom = 12.dp)
        ) {
            // Header row: "Recent drives" and "See all"
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Recent drives",
                    color = colors.ink,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Text(
                    text = "See all",
                    color = colors.ink2,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.clickable { onNavigateTab(AerisNavTab.TRIPS) }
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Horizontal row of drive cards
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                DriveCard(
                    drive = bundledDrive,
                    onClick = { onSelectDrive(bundledDrive) }
                )
            }
        }

        // 5. Bottom Navigation Bar
        AerisBottomNav(
            selectedTab = AerisNavTab.EXPLORE,
            onTabSelected = onNavigateTab,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

/**
 * Dedicated Mapbox View for Explore Screen.
 */
@Composable
private fun ExploreMapView(
    positionState: PositionState?,
    mapStyle: AerisMapStyle,
    bundledDrive: Drive,
    showDrivePaths: Boolean,
    zoomTrigger: Int,
    zoomOutTrigger: Int,
    locateTrigger: Int,
) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    var cameraSet by remember { mutableStateOf(false) }
    var loadedStyleUri by remember { mutableStateOf<String?>(null) }
    var lastZoomTrigger by remember { mutableStateOf(zoomTrigger) }
    var lastZoomOutTrigger by remember { mutableStateOf(zoomOutTrigger) }
    var lastLocateTrigger by remember { mutableStateOf(locateTrigger) }

    val pointManager = remember { mutableStateOf<PointAnnotationManager?>(null) }
    val polyManager = remember { mutableStateOf<PolylineAnnotationManager?>(null) }
    val drivePathAnno = remember { mutableStateOf<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation?>(null) }

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
            // Load Mapbox Dark/Light style per V0 § 1 & V1 § 1
            if (loadedStyleUri != mapStyle.mapboxUri) {
                mv.mapboxMap.loadStyleUri(mapStyle.mapboxUri)
                loadedStyleUri = mapStyle.mapboxUri
            }

            val lat = positionState?.lat ?: bundledDrive.points.firstOrNull()?.lat ?: 52.3704
            val lon = positionState?.lon ?: bundledDrive.points.firstOrNull()?.lon ?: -1.2544

            if (!cameraSet) {
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(Point.fromLngLat(lon, lat))
                        .zoom(14.0)
                        .pitch(0.0)
                        .bearing(0.0)
                        .build()
                )
                cameraSet = true
            }

            // Handle Zoom In
            if (zoomTrigger != lastZoomTrigger) {
                lastZoomTrigger = zoomTrigger
                val curZoom = mv.mapboxMap.cameraState.zoom
                mv.mapboxMap.setCamera(CameraOptions.Builder().zoom(curZoom + 1.0).build())
            }

            // Handle Zoom Out
            if (zoomOutTrigger != lastZoomOutTrigger) {
                lastZoomOutTrigger = zoomOutTrigger
                val curZoom = mv.mapboxMap.cameraState.zoom
                mv.mapboxMap.setCamera(CameraOptions.Builder().zoom(curZoom - 1.0).build())
            }

            // Handle Locate
            if (locateTrigger != lastLocateTrigger) {
                lastLocateTrigger = locateTrigger
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(Point.fromLngLat(lon, lat))
                        .zoom(15.5)
                        .build()
                )
            }

            if (polyManager.value == null) {
                polyManager.value = mv.annotations.createPolylineAnnotationManager()
            }
            if (pointManager.value == null) {
                pointManager.value = mv.annotations.createPointAnnotationManager()
            }

            val pm = polyManager.value ?: return@AndroidView

            // Draw recent drive path faintly when Drives chip is active (R3 § 5)
            if (showDrivePaths && bundledDrive.points.size >= 2) {
                if (drivePathAnno.value == null) {
                    val pts = bundledDrive.points.map { Point.fromLngLat(it.lon, it.lat) }
                    drivePathAnno.value = pm.create(
                        PolylineAnnotationOptions()
                            .withPoints(pts)
                            .withLineColor("#6D8BFF")
                            .withLineWidth(2.5)
                            .withLineOpacity(0.4)
                    )
                }
            } else {
                drivePathAnno.value?.let { pm.delete(it) }
                drivePathAnno.value = null
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
