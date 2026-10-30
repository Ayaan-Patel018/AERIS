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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
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
import com.aeris.mobile.domain.routing.RouteOption
import com.aeris.mobile.domain.routing.RoutePreviewData
import com.aeris.mobile.domain.routing.RoutingService
import com.aeris.mobile.ui.components.AerisMapStyle
import com.aeris.mobile.ui.theme.Aeris
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.MapView
import com.mapbox.maps.plugin.annotation.annotations
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.createPolylineAnnotationManager
import com.mapbox.maps.plugin.scalebar.scalebar

/**
 * Route Preview Screen in Day theme matching Mockup 00 Screen 3 & R4 § 1–3.
 */
@Composable
fun RoutePreviewScreen(
    destinationName: String,
    toLat: Double,
    toLon: Double,
    onStartNavigation: (RouteOption) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = Aeris.colors

    var previewData by remember { mutableStateOf<RoutePreviewData?>(null) }
    var selectedRouteIndex by remember { mutableStateOf(0) }

    LaunchedEffect(toLat, toLon) {
        previewData = RoutingService.fetchRoutes(
            fromLat = 52.3704,
            fromLon = -1.2544,
            toLat = toLat,
            toLon = toLon,
            destinationName = destinationName
        )
    }

    val selectedRoute = previewData?.routes?.getOrNull(selectedRouteIndex)

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        // 1. Full-bleed Map View in Day Theme (per Mockup Screen 3)
        RoutePreviewMapView(
            previewData = previewData,
            selectedRouteIndex = selectedRouteIndex
        )

        // 2. Top Card: Origin & Destination Inputs + Chips
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .shadow(8.dp, RoundedCornerShape(20.dp), ambientColor = colors.ink.copy(alpha = 0.12f))
                    .clip(RoundedCornerShape(20.dp))
                    .background(colors.paper)
                    .border(1.dp, colors.harbor, RoundedCornerShape(20.dp))
                    .padding(16.dp)
            ) {
                Column {
                    // Back button row + From input
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .clickable { onBack() },
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = "Back",
                                tint = colors.ink,
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        Spacer(modifier = Modifier.width(10.dp))

                        // Hollow circle (origin indicator)
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .border(2.dp, colors.ink3, CircleShape)
                        )

                        Spacer(modifier = Modifier.width(12.dp))

                        Text(
                            text = "Your location",
                            color = colors.ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Destination input row
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(start = 42.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Solid black dot (destination indicator)
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(colors.ink)
                        )

                        Spacer(modifier = Modifier.width(12.dp))

                        Text(
                            text = destinationName,
                            color = colors.ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Filter chips: [Driving], [Avoid tolls]
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(16.dp))
                                .background(colors.cobaltSoft)
                                .border(1.dp, colors.cobalt, RoundedCornerShape(16.dp))
                                .padding(horizontal = 14.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "Driving",
                                color = colors.cobalt,
                                fontSize = 12.5.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(16.dp))
                                .background(colors.paper)
                            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
                            .padding(horizontal = 14.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "Avoid tolls",
                                color = colors.ink2,
                                fontSize = 12.5.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
            }
        }

        // 3. Bottom Sheet: Route Options & Start button
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .padding(20.dp)
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

            // Route alternatives list
            previewData?.routes?.forEachIndexed { index, route ->
                val isSelected = index == selectedRouteIndex

                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (isSelected) colors.chalk else androidx.compose.ui.graphics.Color.Transparent)
                        .clickable { selectedRouteIndex = index }
                        .padding(horizontal = 12.dp, vertical = 10.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${route.durationMinutes} min",
                            color = colors.ink,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                        )

                        Spacer(modifier = Modifier.width(16.dp))

                        val subtitle = if (route.label.isNotBlank()) {
                            "${String.format(java.util.Locale.getDefault(), "%.1f km", route.distanceKm)} • ${route.label}"
                        } else {
                            String.format(java.util.Locale.getDefault(), "%.1f km", route.distanceKm)
                        }

                        Text(
                            text = subtitle,
                            color = colors.ink2,
                            fontSize = 13.5.sp,
                        )
                    }

                    // Warning hint if route passes user's recorded satellite-loss spots
                    if (route.passesSatelliteLossSpots > 0 && isSelected) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(colors.cobaltSoft.copy(alpha = 0.6f))
                                .padding(horizontal = 10.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(colors.amberLine)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Passes 1 satellite-loss spot from your drives",
                                color = colors.ink,
                                fontSize = 11.5.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Start Guidance button row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    onClick = {
                        selectedRoute?.let { onStartNavigation(it) }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colors.ink,
                        contentColor = colors.paper
                    ),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .weight(1.8f)
                        .height(52.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Start",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                OutlinedButton(
                    onClick = { /* Open turn list */ },
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = colors.ink
                    ),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .weight(1f)
                        .height(52.dp)
                ) {
                    Text(
                        text = "Steps",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}


@Composable
private fun RoutePreviewMapView(
    previewData: RoutePreviewData?,
    selectedRouteIndex: Int,
) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    var cameraCentered by remember { mutableStateOf(false) }
    var styleLoaded by remember { mutableStateOf(false) }
    var lastRenderedIndex by remember { mutableStateOf(-1) }

    val polyManager = remember { mutableStateOf<PolylineAnnotationManager?>(null) }
    val polyAnnotations = remember { mutableStateOf<List<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation>>(emptyList()) }

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
            // Load Mapbox Light style (Day preview per R4 § 1)
            if (!styleLoaded) {
                mv.mapboxMap.loadStyleUri(com.mapbox.maps.Style.LIGHT)
                styleLoaded = true
            }

            if (previewData == null) return@AndroidView

            if (!cameraCentered) {
                val origin = previewData.origin
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(origin)
                        .zoom(14.2)
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

            // Only rebuild polylines when route selection or preview changes
            if (lastRenderedIndex != selectedRouteIndex || polyAnnotations.value.isEmpty()) {
                lastRenderedIndex = selectedRouteIndex
                polyAnnotations.value.forEach { pm.delete(it) }
                val newAnnos = mutableListOf<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation>()

                // Draw alternative routes first (Slate)
                previewData.routes.forEachIndexed { idx, route ->
                    if (idx != selectedRouteIndex && route.points.size >= 2) {
                        val anno = pm.create(
                            PolylineAnnotationOptions()
                                .withPoints(route.points)
                                .withLineColor("#8493A0")
                                .withLineWidth(4.0)
                                .withLineOpacity(0.7)
                        )
                        newAnnos.add(anno)
                    }
                }

                // Draw active selected route (Cobalt)
                val active = previewData.routes.getOrNull(selectedRouteIndex)
                if (active != null && active.points.size >= 2) {
                    val anno = pm.create(
                        PolylineAnnotationOptions()
                            .withPoints(active.points)
                            .withLineColor("#2D5BFF")
                            .withLineWidth(6.0)
                            .withLineOpacity(1.0)
                    )
                    newAnnos.add(anno)
                }

                polyAnnotations.value = newAnnos
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
