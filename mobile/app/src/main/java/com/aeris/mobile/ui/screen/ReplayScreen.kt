package com.aeris.mobile.ui.screen

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import kotlinx.coroutines.delay
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.aeris.mobile.domain.adapter.AerisTripAdapter
import com.aeris.mobile.domain.math.EllipseMath
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.domain.playback.DriveMoments
import com.aeris.mobile.domain.playback.MomentKind
import com.aeris.mobile.domain.playback.PlaybackBanner
import com.aeris.mobile.domain.playback.PlaybackClock
import com.aeris.mobile.domain.playback.TrackSegments
import com.aeris.mobile.ui.components.AerisMapStyle
import com.aeris.mobile.ui.components.LayersButton
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.MapView
import com.mapbox.maps.plugin.annotation.annotations
import com.mapbox.maps.plugin.annotation.generated.CircleAnnotation
import com.mapbox.maps.plugin.annotation.generated.CircleAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.CircleAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.PointAnnotation
import com.mapbox.maps.plugin.annotation.generated.PolygonAnnotation
import com.mapbox.maps.plugin.annotation.generated.PolygonAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation
import com.mapbox.maps.plugin.annotation.generated.createCircleAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.PolygonAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.createPointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.createPolygonAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.createPolylineAnnotationManager
import com.mapbox.maps.plugin.scalebar.scalebar
import kotlin.math.roundToInt

/**
 * Trip Playback Screen matching Mockup 00 Screen 5 & R5 § 3.
 *
 * Dedicated drive replay session:
 * - Persistent honesty chip: "Playing recorded drive • {label}"
 * - Outage banner with live counter
 * - Speed and 16-point cardinal heading
 * - Position uncertainty (amber in outage, teal when locked)
 * - Moment cards carousel
 * - Distance-driven progress rail with speed multiplier pill
 */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun ReplayScreen(
    drive: Drive,
    playbackClock: PlaybackClock,
    isNightTheme: Boolean,
    onToggleNightTheme: (Boolean) -> Unit,
    onBack: () -> Unit = {},
    onOpenDashView: () -> Unit = {},
    onOpenRecordMode: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    val currentIndex by playbackClock.currentIndex.collectAsState()
    val isPlaying by playbackClock.isPlaying.collectAsState()
    val playbackSpeed by playbackClock.playbackSpeed.collectAsState()
    val currentPoint by playbackClock.currentPoint.collectAsState()
    val activeOutage by playbackClock.activeOutage.collectAsState()
    val currentFraction by playbackClock.currentFraction.collectAsState()
    val elapsedSeconds by playbackClock.elapsedSeconds.collectAsState()
    val distanceDrivenMeters by playbackClock.distanceDrivenMeters.collectAsState()

    var selectedMapStyle by remember {
        mutableStateOf(if (isNightTheme) AerisMapStyle.AERIS_NIGHT else AerisMapStyle.AERIS_DAY)
    }
    var showOverflow by remember { mutableStateOf(false) }
    var compareOutage by remember { mutableStateOf<com.aeris.mobile.domain.model.OutageWindow?>(null) }
    var preRollActive by remember { mutableStateOf(true) }
    var showAbout by remember { mutableStateOf(false) }

    LaunchedEffect(drive) {
        playbackClock.attachDrive(drive)
        // 1.2 s pre-roll camera settle then start clock per R5 § 3.6
        delay(1200L)
        preRollActive = false
        playbackClock.play()
    }

    val isOutage = activeOutage != null

    var isCameraFollow by remember { mutableStateOf(true) }
    var zoomInTrigger by remember { mutableStateOf(0) }
    var zoomOutTrigger by remember { mutableStateOf(0) }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.chalk)
            .clickable(
                enabled = preRollActive,
                onClick = {
                    preRollActive = false
                    playbackClock.play()
                }
            )
    ) {
        // 1. Map Canvas (Flat pitch 0, heading-up, middle third per R5 § 3.3)
        PlaybackMapView(
            drive = drive,
            currentPoint = currentPoint,
            currentIndex = currentIndex,
            isOutage = isOutage,
            mapStyle = selectedMapStyle,
            isCameraFollow = isCameraFollow,
            zoomInTrigger = zoomInTrigger,
            zoomOutTrigger = zoomOutTrigger
        )

        // 2. Top-left Persistent Honesty Chip per R5 § 3.1 (tap opens Trip detail)
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .statusBarsPadding()
                .padding(start = 16.dp, top = 8.dp)
                .height(34.dp)
                .shadow(4.dp, RoundedCornerShape(17.dp), ambientColor = colors.ink.copy(alpha = 0.12f))
                .clip(RoundedCornerShape(17.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(17.dp))
                .clickable(
                    role = Role.Button,
                    onClick = {
                        playbackClock.pause()
                        onBack()
                    }
                )
                .padding(horizontal = 12.dp),
            contentAlignment = Alignment.Center
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.PlayArrow,
                    contentDescription = null,
                    tint = colors.ink2,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Playing recorded drive • ${drive.meta.id}",
                    color = colors.ink2,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // Top-right Controls: Layers button + Overflow Menu per R5 § 3.5
        Row(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .statusBarsPadding()
                .padding(end = 16.dp, top = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            LayersButton(
                onClick = {
                    selectedMapStyle = if (selectedMapStyle == AerisMapStyle.AERIS_NIGHT) {
                        AerisMapStyle.AERIS_DAY
                    } else {
                        AerisMapStyle.AERIS_NIGHT
                    }
                }
            )

            Box {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, CircleShape)
                        .clickable(role = Role.Button) { showOverflow = true },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.MoreVert,
                        contentDescription = "Options",
                        tint = colors.ink,
                        modifier = Modifier.size(20.dp)
                    )
                }

                DropdownMenu(
                    expanded = showOverflow,
                    onDismissRequest = { showOverflow = false }
                ) {
                    DropdownMenuItem(
                        text = { Text("Dash view", color = colors.ink) },
                        onClick = {
                            showOverflow = false
                            onOpenDashView()
                        }
                    )
                    DropdownMenuItem(
                        text = { Text("About this run", color = colors.ink) },
                        onClick = {
                            showOverflow = false
                            showAbout = true
                        }
                    )
                    DropdownMenuItem(
                        text = { Text("Share this moment", color = colors.ink) },
                        onClick = { showOverflow = false }
                    )
                }
            }
        }

        // 3. Banner: inside outages[] (simulated outage), or outside when the last phone fix is > 15 s old
        val bannerText = PlaybackBanner.textFor(currentPoint, activeOutage)
        AnimatedVisibility(
            visible = bannerText != null,
            enter = fadeIn(),
            exit = fadeOut(),
            modifier = Modifier
                .align(Alignment.TopCenter)
                .statusBarsPadding()
                .padding(top = 52.dp, start = 16.dp, end = 16.dp)
        ) {
            val outageSec = if (activeOutage != null && currentPoint != null) {
                (currentPoint!!.timestampSec - activeOutage!!.startSec).coerceAtLeast(0.0)
            } else null

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .shadow(6.dp, RoundedCornerShape(20.dp), ambientColor = colors.amber.copy(alpha = 0.2f))
                    .clip(RoundedCornerShape(20.dp))
                    .background(colors.amberSoft)
                    .border(1.dp, colors.amber.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
                    .padding(horizontal = 18.dp, vertical = 12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(colors.amberLine)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = bannerText ?: "",
                            color = colors.ink,
                            fontSize = 13.5.sp,
                            fontWeight = FontWeight.Bold,
                            lineHeight = 18.sp
                        )
                    }

                    if (outageSec != null) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = Formatters.formatMmSs(outageSec),
                            color = colors.amberLine,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }

        // 4. Compact Bottom Card (about 226 dp per Mockup Screen 5 & R5 § 3.4)
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .padding(horizontal = 20.dp, vertical = 16.dp)
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

            Spacer(modifier = Modifier.height(10.dp))

            // Row 1: Telemetry Readouts (Speed & Heading on left, Uncertainty on right)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                // Left: Speed + Heading (from the frame; "—" when the frame has none)
                Column {
                    val spd = currentPoint?.speedMps?.let { "${(it * 3.6).roundToInt()} km/h" } ?: "— km/h"
                    Text(
                        text = spd,
                        color = colors.ink,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 30.sp
                    )
                    Spacer(modifier = Modifier.height(1.dp))
                    val headingDeg = currentPoint?.headingDeg
                    Text(
                        text = if (headingDeg != null) {
                            "heading ${headingDeg.roundToInt() % 360}° ${Formatters.cardinal16(headingDeg)}"
                        } else "heading —",
                        color = colors.ink2,
                        fontSize = 12.sp,
                    )
                }

                // Right: the filter's own 1-sigma (major semi-axis); not calibrated (meta.sigma.calibrated)
                Column(horizontalAlignment = Alignment.End) {
                    val uncM = currentPoint?.sigmaMajorM
                    Text(
                        text = if (uncM != null) "±${Formatters.formatMeters(uncM)}" else "—",
                        color = if (isOutage) colors.amberLine else colors.teal,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 30.sp
                    )
                    Spacer(modifier = Modifier.height(1.dp))
                    Text(
                        text = if (drive.meta.sigmaCalibrated == false) "1σ major axis, not calibrated" else "position uncertainty, 1σ",
                        color = colors.ink2,
                        fontSize = 12.sp,
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Row 2: Moments derived from outages[] and corrections[], with Previous & Next buttons
            val moments = remember(drive) { DriveMoments.build(drive) }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Previous moment button '‹'
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, CircleShape)
                        .clickable(role = Role.Button) {
                            val prev = moments.lastOrNull { it.index < currentIndex }
                            playbackClock.seekToIndex(prev?.index ?: 0)
                        }
                        .semantics {
                            role = Role.Button
                            contentDescription = "Previous moment"
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "‹", color = colors.ink, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }

                // Horizontally scrolling moment cards (long press on an outage moment opens the compare sheet)
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (moments.isEmpty()) {
                        Text(text = "No moments in this drive", color = colors.ink3, fontSize = 12.sp)
                    }
                    moments.forEach { m ->
                        MomentCard(
                            iconText = when (m.kind) {
                                MomentKind.GNSS_WITHHELD -> "∿"
                                MomentKind.GNSS_BACK -> "✓"
                                MomentKind.CORRECTION -> "↯"
                            },
                            title = m.title,
                            time = Formatters.formatMmSs(m.tSec),
                            isActive = m.kind == MomentKind.GNSS_WITHHELD && activeOutage != null && activeOutage?.id == m.outage?.id,
                            isAmber = m.kind != MomentKind.GNSS_BACK,
                            onClick = { playbackClock.seekToIndex(m.index) },
                            onLongClick = { m.outage?.let { compareOutage = it } }
                        )
                    }
                }

                // Next moment button '›'
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, CircleShape)
                        .clickable(role = Role.Button) {
                            val next = moments.firstOrNull { it.index > currentIndex }
                            playbackClock.seekToIndex(next?.index ?: (drive.points.size - 1).coerceAtLeast(0))
                        }
                        .semantics {
                            role = Role.Button
                            contentDescription = "Next moment"
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "›", color = colors.ink, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Row 3: Progress Rail (6 dp, distance-based progress per R5 § 3.4)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(24.dp)
                    .pointerInput(drive) {
                        detectTapGestures { offset ->
                            val fraction = (offset.x / size.width).coerceIn(0f, 1f)
                            playbackClock.seekToFraction(fraction)
                        }
                    },
                contentAlignment = Alignment.CenterStart
            ) {
                Canvas(modifier = Modifier.fillMaxWidth().height(6.dp)) {
                    val w = size.width
                    val h = size.height

                    // Background rail
                    drawRoundRect(
                        color = colors.harbor,
                        size = Size(w, h),
                        cornerRadius = CornerRadius(h / 2, h / 2)
                    )

                    // Outage windows from outages[], positioned by frame index (same scale as currentFraction)
                    val lastIdx = (drive.points.size - 1).coerceAtLeast(1).toFloat()
                    for (o in drive.outages) {
                        drawRoundRect(
                            color = colors.amberLine,
                            topLeft = Offset(o.startIndex / lastIdx * w, 0f),
                            size = Size((o.endIndex - o.startIndex) / lastIdx * w, h),
                            cornerRadius = CornerRadius(2f, 2f)
                        )
                    }

                    // Travelled progress
                    val progW = (currentFraction * w).coerceIn(0f, w)
                    drawRoundRect(
                        color = colors.cobalt,
                        size = Size(progW, h),
                        cornerRadius = CornerRadius(h / 2, h / 2)
                    )

                    // Slider thumb
                    drawCircle(
                        color = if (isOutage) colors.amberLine else colors.cobalt,
                        radius = 8.dp.toPx(),
                        center = Offset(progW, h / 2)
                    )
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            // Controls Row: "Driven X of Y km" + Speed Chip + Play/Pause button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Driven distance readout
                val drivenKm = Formatters.formatDistance(distanceDrivenMeters)
                val totalKm = Formatters.formatDistance(drive.meta.totalDistanceMeters)
                Text(
                    text = "Driven $drivenKm of $totalKm",
                    color = colors.ink2,
                    fontSize = 12.5.sp,
                    fontWeight = FontWeight.Medium
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Speed multiplier chip ("2x" - tap cycles 1x, 2x, 4x, 8x per R5 § 3.4)
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(14.dp))
                            .background(colors.chalk)
                            .border(1.dp, colors.harbor, RoundedCornerShape(14.dp))
                            .clickable { playbackClock.cycleSpeed() }
                            .padding(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "${playbackSpeed.toInt()}x",
                            color = colors.ink,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    // 44 dp round Play/Pause Button
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(colors.ink)
                            .clickable(role = Role.Button) { playbackClock.togglePlayPause() }
                            .semantics {
                                role = Role.Button
                                contentDescription = if (isPlaying) "Pause playback" else "Play playback"
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        if (isPlaying) {
                            Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
                                Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                                Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                            }
                        } else {
                            Icon(
                                imageVector = Icons.Default.PlayArrow,
                                contentDescription = null,
                                tint = colors.paper,
                                modifier = Modifier.size(22.dp)
                            )
                        }
                    }
                }
            }
        }

        // 4b. Floating Map Controls: Zoom In (+), Zoom Out (−), and Follow Car / Re-center per V0 § 2 / V2
        Column(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = 270.dp)
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
                    .clickable(role = Role.Button) { zoomInTrigger++ }
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

            Box(
                modifier = Modifier
                    .width(32.dp)
                    .height(1.dp)
                    .background(colors.harbor)
            )

            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(if (isCameraFollow) colors.cobaltSoft else colors.paper)
                    .clickable(role = Role.Button) { isCameraFollow = !isCameraFollow }
                    .semantics {
                        role = Role.Button
                        contentDescription = if (isCameraFollow) "Free camera pan" else "Follow vehicle"
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.LocationOn,
                    contentDescription = null,
                    tint = if (isCameraFollow) colors.cobalt else colors.ink3,
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        // 5. Trip Finished Summary Card per R5 § 3.6
        AnimatedVisibility(
            visible = currentFraction >= 0.99f,
            enter = fadeIn(),
            exit = fadeOut(),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 24.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .shadow(16.dp, RoundedCornerShape(20.dp), ambientColor = colors.ink.copy(alpha = 0.2f))
                    .clip(RoundedCornerShape(20.dp))
                    .background(colors.paper)
                    .border(1.dp, colors.harbor, RoundedCornerShape(20.dp))
                    .padding(20.dp)
            ) {
                Column {
                    Text(
                        text = "Trip finished",
                        color = colors.ink,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "${Formatters.formatDistance(drive.meta.totalDistanceMeters)} • ${(drive.meta.durationSec / 60).toInt()} min • ${drive.outages.size} satellite loss",
                        color = colors.ink2,
                        fontSize = 13.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    val firstOutage = drive.outages.firstOrNull()
                    val jump = firstOutage?.let { DriveMoments.firstCorrectionAfter(drive, it) }
                    val metrics = drive.metrics
                    val summary = buildString {
                        if (jump != null) {
                            append(String.format(java.util.Locale.US, "At the first fix after the outage AERIS jumped %.1f m.", jump.jumpM))
                        }
                        if (metrics != null) {
                            if (isNotEmpty()) append(" ")
                            append(
                                String.format(
                                    java.util.Locale.US,
                                    "Scored against the VBOX reference (development drive, in-sample): mean error %.1f m, end error %s over the outage.",
                                    metrics.meanErrorMeters,
                                    metrics.endErrorMeters?.let { String.format(java.util.Locale.US, "%.1f m", it) } ?: "—"
                                )
                            )
                        }
                        if (isEmpty()) append("—")
                    }
                    Text(
                        text = summary,
                        color = colors.ink,
                        fontSize = 12.5.sp,
                        lineHeight = 17.sp
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Button(
                            onClick = {
                                playbackClock.seekToFraction(0f)
                                playbackClock.play()
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = colors.ink,
                                contentColor = colors.paper
                            ),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1.5f).height(46.dp)
                        ) {
                            Text("Play again", fontWeight = FontWeight.Bold)
                        }
                        OutlinedButton(
                            onClick = {
                                playbackClock.pause()
                                onBack()
                            },
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1f).height(46.dp)
                        ) {
                            Text("Back to trip", color = colors.ink)
                        }
                    }
                }
            }
        }

        // 6. Compare Sheet if opened per R5 § 6
        if (compareOutage != null) {
            com.aeris.mobile.ui.sheet.CompareSheet(
                outage = compareOutage,
                drive = drive,
                onPlayMoment = { t ->
                    compareOutage = null
                    playbackClock.seekToSeconds(t)
                    playbackClock.play()
                },
                onDismiss = { compareOutage = null }
            )
        }

        if (showAbout) {
            AboutRunDialog(drive = drive, onDismiss = { showAbout = false })
        }
    }
}

@Composable
private fun MomentCard(
    iconText: String,
    title: String,
    time: String,
    isActive: Boolean,
    isAmber: Boolean,
    onClick: () -> Unit,
    onLongClick: () -> Unit = {},
) {
    val colors = Aeris.colors

    val borderCol = when {
        isActive && isAmber -> colors.amberLine
        isActive -> colors.cobalt
        else -> colors.harbor
    }

    val bgCol = when {
        isActive && isAmber -> colors.amberSoft
        isActive -> colors.cobaltSoft
        else -> colors.paper
    }

    Row(
        modifier = Modifier
            .width(136.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(bgCol)
            .border(1.dp, borderCol, RoundedCornerShape(14.dp))
            .pointerInput(Unit) {
                detectTapGestures(
                    onTap = { onClick() },
                    onLongPress = { onLongClick() }
                )
            }
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(24.dp)
                .clip(CircleShape)
                .background(if (isAmber) colors.amberLine.copy(alpha = 0.2f) else colors.chalk),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = iconText,
                color = if (isAmber) colors.amberLine else colors.ink,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        Column {
            Text(
                text = title,
                color = colors.ink,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = time,
                color = colors.ink3,
                fontSize = 10.5.sp,
            )
        }
    }
}

/** Corrections at least this long get a "<jump_m> m" label on the map. */
private const val JUMP_LABEL_MIN_M = 20.0

private const val COLOR_GNSS_FRAME = "#6D8BFF"     // status gnss
private const val COLOR_DR_FRAME = "#F2A93B"       // status dr
private const val COLOR_WARMUP_FRAME = "#8A97A6"   // status warmup
private const val COLOR_GNSS_FIX = "#2DD4BF"

/** Mapbox annotation managers and the annotations currently on the map (created once per MapView). */
private class PlaybackLayers {
    var background: PolylineAnnotationManager? = null
    var ellipse: PolygonAnnotationManager? = null
    var travelled: PolylineAnnotationManager? = null
    var jumps: PolylineAnnotationManager? = null
    var gnss: CircleAnnotationManager? = null
    var labels: PointAnnotationManager? = null
    var backgroundDrawn = false
    var ellipseAnno: PolygonAnnotation? = null
    val travelledAnnos = HashMap<Int, PolylineAnnotation>()
    val travelledEnd = HashMap<Int, Int>()
    val jumpAnnos = HashMap<Int, PolylineAnnotation>()
    val labelAnnos = HashMap<Int, PointAnnotation>()
    val gnssAnnos = HashMap<Int, CircleAnnotation>()
}

private fun frameColor(status: GnssStatus): String = when (status) {
    GnssStatus.HEALTHY -> COLOR_GNSS_FRAME
    GnssStatus.OUTAGE, GnssStatus.DEGRADED -> COLOR_DR_FRAME
    GnssStatus.UNKNOWN -> COLOR_WARMUP_FRAME
}

private fun pointsOf(drive: Drive, from: Int, to: Int): List<Point> =
    (from..to).map { Point.fromLngLat(drive.points[it].lon, drive.points[it].lat) }

/** Closed ring of the frame's own 1-sigma ellipse (sigma_major/minor_m, ellipse_angle_deg); null if the frame has none. */
private fun ellipseRing(p: TrajectoryPoint): List<Point>? {
    val major = p.sigmaMajorM ?: return null
    val minor = p.sigmaMinorM ?: return null
    val angle = p.ellipseAngleDeg ?: return null
    val e = EllipseMath.fromExport(p.lat, p.lon, major, minor, angle)
    return EllipseMath.generatePolygonPoints(e).map { (lat, lon) -> Point.fromLngLat(lon, lat) }
}

/**
 * Replay map. Layers, bottom to top:
 * - whole drive, faint, split at every correction (no solid line across a jump);
 * - the current frame's 1-sigma ellipse;
 * - travelled path, solid, coloured by frame status, split at corrections;
 * - every correction reached so far as a dashed segment (labelled with jump_m when >= 20 m);
 * - phone GNSS fixes up to now, matched by t_s; none inside outages[], and the layer is hidden while an outage is active.
 */
@Composable
private fun PlaybackMapView(
    drive: Drive,
    currentPoint: TrajectoryPoint?,
    currentIndex: Int,
    isOutage: Boolean,
    mapStyle: AerisMapStyle,
    isCameraFollow: Boolean,
    zoomInTrigger: Int,
    zoomOutTrigger: Int,
) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    var cameraCentered by remember { mutableStateOf(false) }
    var loadedStyleUri by remember { mutableStateOf<String?>(null) }
    var lastZoomInTrigger by remember { mutableStateOf(zoomInTrigger) }
    var lastZoomOutTrigger by remember { mutableStateOf(zoomOutTrigger) }

    val layers = remember { PlaybackLayers() }
    val backgroundSegments = remember(drive) { TrackSegments.build(drive.points, drive.corrections, splitOnStatus = false) }
    val travelledSegments = remember(drive) { TrackSegments.build(drive.points, drive.corrections, splitOnStatus = true) }
    val drawableFixes = remember(drive) {
        drive.baselinePoints.indices.filter { k ->
            val t = drive.baselinePoints[k].timestampSec
            drive.outages.none { t >= it.startSec && t <= it.endSec }
        }
    }

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
            if (loadedStyleUri != mapStyle.mapboxUri) {
                mv.mapboxMap.loadStyleUri(mapStyle.mapboxUri)
                loadedStyleUri = mapStyle.mapboxUri
            }

            if (drive.points.isEmpty()) return@AndroidView
            val c = currentIndex.coerceIn(0, drive.points.lastIndex)
            val pt = currentPoint ?: drive.points[c]

            if (!cameraCentered) {
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(Point.fromLngLat(pt.lon, pt.lat))
                        .zoom(17.0)
                        .pitch(0.0)
                        .bearing(pt.headingDeg ?: 0.0)
                        .build()
                )
                cameraCentered = true
            } else if (isCameraFollow) {
                mv.mapboxMap.setCamera(
                    CameraOptions.Builder()
                        .center(Point.fromLngLat(pt.lon, pt.lat))
                        .bearing(pt.headingDeg ?: 0.0)
                        .build()
                )
            }

            if (zoomInTrigger != lastZoomInTrigger) {
                lastZoomInTrigger = zoomInTrigger
                val z = mv.mapboxMap.cameraState.zoom
                mv.mapboxMap.setCamera(CameraOptions.Builder().zoom(z + 1.0).build())
            }
            if (zoomOutTrigger != lastZoomOutTrigger) {
                lastZoomOutTrigger = zoomOutTrigger
                val z = mv.mapboxMap.cameraState.zoom
                mv.mapboxMap.setCamera(CameraOptions.Builder().zoom(z - 1.0).build())
            }

            // Managers in z-order (created first = drawn lowest)
            if (layers.background == null) {
                val annotations = mv.annotations
                layers.background = annotations.createPolylineAnnotationManager()
                layers.ellipse = annotations.createPolygonAnnotationManager()
                layers.travelled = annotations.createPolylineAnnotationManager()
                layers.jumps = annotations.createPolylineAnnotationManager().apply { lineDasharray = listOf(2.0, 1.5) }
                layers.gnss = annotations.createCircleAnnotationManager()
                layers.labels = annotations.createPointAnnotationManager()
            }
            val bgManager = layers.background ?: return@AndroidView
            val ellipseManager = layers.ellipse ?: return@AndroidView
            val travelledManager = layers.travelled ?: return@AndroidView
            val jumpManager = layers.jumps ?: return@AndroidView
            val gnssManager = layers.gnss ?: return@AndroidView
            val labelManager = layers.labels ?: return@AndroidView

            // 1. Whole drive, faint, once
            if (!layers.backgroundDrawn) {
                for (seg in backgroundSegments) {
                    if (seg.end <= seg.start) continue
                    bgManager.create(
                        PolylineAnnotationOptions()
                            .withPoints(pointsOf(drive, seg.start, seg.end))
                            .withLineColor("#3A4B5D")
                            .withLineWidth(3.5)
                            .withLineOpacity(0.4)
                    )
                }
                layers.backgroundDrawn = true
            }

            // 2. Travelled path up to the current frame (only changed segments touch the map)
            travelledSegments.forEachIndexed { k, seg ->
                val want = if (seg.start >= c) -1 else minOf(seg.end, c)
                val have = layers.travelledEnd[k] ?: -1
                if (want == have) return@forEachIndexed
                val existing = layers.travelledAnnos[k]
                if (want <= seg.start) {
                    existing?.let { travelledManager.delete(it) }
                    layers.travelledAnnos.remove(k)
                    layers.travelledEnd.remove(k)
                } else {
                    val pts = pointsOf(drive, seg.start, want)
                    if (existing == null) {
                        layers.travelledAnnos[k] = travelledManager.create(
                            PolylineAnnotationOptions()
                                .withPoints(pts)
                                .withLineColor(frameColor(seg.status))
                                .withLineWidth(4.5)
                                .withLineOpacity(0.95)
                        )
                    } else {
                        existing.points = pts
                        travelledManager.update(existing)
                    }
                    layers.travelledEnd[k] = want
                }
            }

            // 3. Corrections reached so far: dashed, labelled with jump_m when >= 20 m
            drive.corrections.forEachIndexed { k, corr ->
                val reached = corr.frameIndex <= c
                val anno = layers.jumpAnnos[k]
                if (reached && anno == null) {
                    val from = Point.fromLngLat(corr.fromLon, corr.fromLat)
                    val to = Point.fromLngLat(corr.toLon, corr.toLat)
                    layers.jumpAnnos[k] = jumpManager.create(
                        PolylineAnnotationOptions()
                            .withPoints(listOf(from, to))
                            .withLineColor(COLOR_DR_FRAME)
                            .withLineWidth(3.0)
                            .withLineOpacity(0.95)
                    )
                    if (corr.jumpM >= JUMP_LABEL_MIN_M) {
                        val mid = Point.fromLngLat((corr.fromLon + corr.toLon) / 2.0, (corr.fromLat + corr.toLat) / 2.0)
                        layers.labelAnnos[k] = labelManager.create(
                            PointAnnotationOptions()
                                .withPoint(mid)
                                .withTextField(String.format(java.util.Locale.US, "%.1f m", corr.jumpM))
                                .withTextSize(12.0)
                                .withTextColor(COLOR_DR_FRAME)
                                .withTextHaloColor("#0F1A24")
                                .withTextHaloWidth(1.5)
                        )
                    }
                } else if (!reached && anno != null) {
                    jumpManager.delete(anno)
                    layers.jumpAnnos.remove(k)
                    layers.labelAnnos.remove(k)?.let { labelManager.delete(it) }
                }
            }

            // 4. Phone GNSS fixes with t_s <= frame t_s (matched by time, never by index); hidden during an outage
            val latestFix = if (isOutage) -1 else AerisTripAdapter.latestFixIndexAt(drive.baselinePoints, drive.points[c].timestampSec)
            for (k in drawableFixes) {
                val want = k <= latestFix
                val anno = layers.gnssAnnos[k]
                if (want && anno == null) {
                    val g = drive.baselinePoints[k]
                    layers.gnssAnnos[k] = gnssManager.create(
                        CircleAnnotationOptions()
                            .withPoint(Point.fromLngLat(g.lon, g.lat))
                            .withCircleRadius(4.0)
                            .withCircleColor(COLOR_GNSS_FIX)
                            .withCircleStrokeColor("#FFFFFF")
                            .withCircleStrokeWidth(1.0)
                    )
                } else if (!want && anno != null) {
                    gnssManager.delete(anno)
                    layers.gnssAnnos.remove(k)
                }
            }

            // 5. The current frame's 1-sigma ellipse (filter output; meta.sigma.calibrated = false)
            val ring = ellipseRing(drive.points[c])
            val ellipseAnno = layers.ellipseAnno
            val fill = if (isOutage) COLOR_DR_FRAME else COLOR_GNSS_FRAME
            if (ring == null) {
                ellipseAnno?.let { ellipseManager.delete(it) }
                layers.ellipseAnno = null
            } else if (ellipseAnno == null) {
                layers.ellipseAnno = ellipseManager.create(
                    PolygonAnnotationOptions()
                        .withPoints(listOf(ring))
                        .withFillColor(fill)
                        .withFillOpacity(0.18)
                )
            } else {
                ellipseAnno.points = listOf(ring)
                ellipseAnno.fillColorString = fill
                ellipseManager.update(ellipseAnno)
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
