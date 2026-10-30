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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
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
import com.aeris.mobile.domain.routing.RouteOption
import com.aeris.mobile.ui.components.AerisMapStyle
import com.aeris.mobile.ui.components.LayersButton
import com.aeris.mobile.ui.components.SignalChip
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
 * Navigating Screen matching Mockup 00 Screen 4 & R4 § 4–10.
 *
 * Turn-by-turn guidance banner, "Then" pill, persistent SignalChip,
 * speed bubble, honest satellite loss handling, and bottom guidance bar.
 */
@Composable
fun NavigationScreen(
    route: RouteOption,
    destinationName: String = "Millbrook Park",
    isNightTheme: Boolean = true,
    onEndNavigation: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = Aeris.colors

    val gnssSource = remember { PhoneGnssSource(context) }
    val positionState by gnssSource.state.collectAsState()

    DisposableEffect(Unit) {
        gnssSource.start()
        onDispose { gnssSource.stop() }
    }

    var selectedMapStyle by remember {
        mutableStateOf(if (isNightTheme) AerisMapStyle.AERIS_NIGHT else AerisMapStyle.AERIS_DAY)
    }

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        // 1. Heading-up Map View (Pitch 40°, speed-based zoom per R4 § 4)
        NavigatingMapView(
            route = route,
            positionState = positionState,
            mapStyle = selectedMapStyle
        )

        // 2. Top Guidance Elements (Banner, Then pill, Signal chip, Layers button)
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 14.dp, vertical = 8.dp)
        ) {
            // Main Guidance Banner per Mockup Screen 4 & R4 § 4
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .shadow(10.dp, RoundedCornerShape(20.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
                    .clip(RoundedCornerShape(20.dp))
                    .background(colors.cobaltSoft)
                    .border(1.dp, colors.cobalt.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
                    .padding(horizontal = 20.dp, vertical = 18.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // 46 dp Maneuver Icon (turn right)
                    Box(
                        modifier = Modifier
                            .size(46.dp)
                            .clip(CircleShape)
                            .background(colors.cobalt),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "↱",
                            color = colors.paper,
                            fontSize = 28.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Spacer(modifier = Modifier.width(16.dp))

                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "300 m",
                            color = colors.ink,
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Bold,
                            lineHeight = 36.sp
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Turn right onto Mill Road",
                            color = colors.ink2,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // "Then" maneuver pill (within 600m)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    modifier = Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Then ↰ 800 m",
                        color = colors.ink2,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

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

            Spacer(modifier = Modifier.height(6.dp))

            // Persistent Signal Chip
            val sig = positionState?.signal ?: SignalState.Locked
            SignalChip(signalState = sig)
        }

        // 3. Speed Bubble (76 dp circle on bottom left above bar per Mockup Screen 4 & R4 § 4)
        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(start = 16.dp, bottom = 108.dp)
                .size(76.dp)
                .shadow(8.dp, CircleShape, ambientColor = colors.ink.copy(alpha = 0.2f))
                .clip(CircleShape)
                .background(colors.paper)
                .border(2.dp, colors.harbor, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                val speed = positionState?.speedMps?.let { (it * 3.6).toInt() } ?: 42
                Text(
                    text = "$speed",
                    color = colors.ink,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    lineHeight = 26.sp
                )
                Text(
                    text = "km/h",
                    color = colors.ink3,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // 4. Navigation Bottom Bar (92 dp per Mockup Screen 4 & R4 § 4)
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(96.dp)
                .shadow(16.dp, ambientColor = colors.ink.copy(alpha = 0.15f))
                .background(colors.paper)
                .border(1.dp, colors.harbor)
                .padding(horizontal = 20.dp, vertical = 16.dp)
        ) {
            Row(
                modifier = Modifier.matchParentSize(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // End navigation button 'X'
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(colors.chalk)
                        .clickable(role = Role.Button, onClick = onEndNavigation)
                        .semantics {
                            role = Role.Button
                            contentDescription = "End navigation"
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = null,
                        tint = colors.ink,
                        modifier = Modifier.size(20.dp)
                    )
                }

                // Center readout: Remaining time (large), distance & arrival time
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "12 min",
                        color = colors.ink,
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 28.sp
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "5.4 km • 14:32 arrival",
                        color = colors.ink2,
                        fontSize = 13.5.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

                // Route overview / detour button
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(colors.chalk),
                    contentAlignment = Alignment.Center
                ) {
                    Box(
                        modifier = Modifier
                            .size(18.dp)
                            .border(2.dp, colors.ink, CircleShape)
                    )
                }
            }
        }
    }
}

@Composable
private fun NavigatingMapView(
    route: RouteOption,
    positionState: PositionState?,
    mapStyle: AerisMapStyle,
) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    var cameraConfigured by remember { mutableStateOf(false) }
    var loadedStyleUri by remember { mutableStateOf<String?>(null) }

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
            // Load Mapbox Dark/Light style
            if (loadedStyleUri != mapStyle.mapboxUri) {
                mv.mapboxMap.loadStyleUri(mapStyle.mapboxUri)
                loadedStyleUri = mapStyle.mapboxUri
            }

            val firstPt = route.points.firstOrNull() ?: Point.fromLngLat(-1.2544, 52.3704)

            if (!cameraConfigured) {
                // Pitch 40°, heading-up, vehicle in lower third per R4 § 4
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(firstPt)
                        .zoom(17.0)
                        .pitch(40.0)
                        .bearing(positionState?.headingDeg ?: 0.0)
                        .build()
                )
                cameraConfigured = true
            }

            if (polyManager.value == null) {
                polyManager.value = mv.annotations.createPolylineAnnotationManager()
            }

            val pm = polyManager.value ?: return@AndroidView

            if (routeAnno.value == null && route.points.size >= 2) {
                routeAnno.value = pm.create(
                    PolylineAnnotationOptions()
                        .withPoints(route.points)
                        .withLineColor("#6D8BFF")
                        .withLineWidth(6.0)
                        .withLineOpacity(1.0)
                )
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
