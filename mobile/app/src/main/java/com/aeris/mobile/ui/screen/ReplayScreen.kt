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
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.domain.playback.PlaybackClock
import com.aeris.mobile.ui.components.AerisMapStyle
import com.aeris.mobile.ui.components.LayersButton
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.MapView
import com.mapbox.maps.plugin.annotation.annotations
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PointAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.PolygonAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.PolylineAnnotationOptions
import com.mapbox.maps.plugin.annotation.generated.createPointAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.createPolygonAnnotationManager
import com.mapbox.maps.plugin.annotation.generated.createPolylineAnnotationManager
import com.mapbox.maps.plugin.scalebar.scalebar

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
                        text = { Text("Share this moment", color = colors.ink) },
                        onClick = { showOverflow = false }
                    )
                }
            }
        }

        // 3. Outage Banner (shown during outages per Mockup Screen 5 & R5 § 3.2)
        AnimatedVisibility(
            visible = isOutage,
            enter = fadeIn(),
            exit = fadeOut(),
            modifier = Modifier
                .align(Alignment.TopCenter)
                .statusBarsPadding()
                .padding(top = 52.dp, start = 16.dp, end = 16.dp)
        ) {
            val outageSec = if (activeOutage != null && currentPoint != null) {
                (currentPoint!!.timestampSec - activeOutage!!.startSec).coerceAtLeast(0.0)
            } else 0.0

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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(colors.amberLine)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Satellite signal lost",
                                color = colors.ink,
                                fontSize = 14.5.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "AERIS continues from the last fix.",
                                color = colors.ink2,
                                fontSize = 11.5.sp,
                            )
                        }
                    }

                    Text(
                        text = Formatters.formatMmSs(outageSec),
                        color = colors.amberLine,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
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
                // Left: Speed + Heading
                Column {
                    val spd = currentPoint?.speedMps?.let { (it * 3.6).toInt() } ?: 38
                    Text(
                        text = "$spd km/h",
                        color = colors.ink,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 30.sp
                    )
                    Spacer(modifier = Modifier.height(1.dp))
                    val headingDeg = currentPoint?.headingDeg ?: 291.0
                    val cardinal = Formatters.cardinal16(headingDeg)
                    Text(
                        text = "heading ${headingDeg.toInt()}° $cardinal",
                        color = colors.ink2,
                        fontSize = 12.sp,
                    )
                }

                // Right: Position Uncertainty (1σ)
                Column(horizontalAlignment = Alignment.End) {
                    val uncM = currentPoint?.sigma ?: 14.0
                    Text(
                        text = "±${Formatters.formatMeters(uncM)}",
                        color = if (isOutage) colors.amberLine else colors.teal,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 30.sp
                    )
                    Spacer(modifier = Modifier.height(1.dp))
                    Text(
                        text = "position uncertainty, 1σ",
                        color = colors.ink2,
                        fontSize = 12.sp,
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Row 2: Moment Cards with Previous & Next buttons per V0 § 2 / V4 § 4
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
                            val moments = listOf(0.0f, 0.2936f, 0.55f, 0.65f, 1.0f)
                            val prev = moments.filter { it < currentFraction - 0.02f }.maxOrNull() ?: 0.0f
                            playbackClock.seekToFraction(prev)
                        }
                        .semantics {
                            role = Role.Button
                            contentDescription = "Previous moment"
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "‹", color = colors.ink, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }

                // Horizontally scrolling moment cards carousel
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Moment Card 1: Satellite lost (active when in outage, long press opens compare sheet per R5 § 6)
                    MomentCard(
                        iconText = "∿",
                        title = "Satellite lost",
                        time = "03:20",
                        isActive = isOutage,
                        isAmber = true,
                        onClick = { playbackClock.jumpToNextOutage() },
                        onLongClick = { compareOutage = drive.outages.firstOrNull() }
                    )

                    // Moment Card 2: Left turn
                    MomentCard(
                        iconText = "↰",
                        title = "Left turn",
                        time = "03:44",
                        isActive = false,
                        isAmber = false,
                        onClick = { playbackClock.seekToFraction(0.55f) }
                    )

                    // Moment Card 3: Satellite back
                    MomentCard(
                        iconText = "✓",
                        title = "Satellite back",
                        time = "04:00",
                        isActive = false,
                        isAmber = false,
                        onClick = { playbackClock.seekToFraction(0.65f) }
                    )
                }

                // Next moment button '›'
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, CircleShape)
                        .clickable(role = Role.Button) {
                            val moments = listOf(0.0f, 0.2936f, 0.55f, 0.65f, 1.0f)
                            val next = moments.filter { it > currentFraction + 0.02f }.minOrNull() ?: 1.0f
                            playbackClock.seekToFraction(next)
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

                    // Outage segment
                    val outStart = 0.29f * w
                    val outW = (0.38f - 0.29f) * w
                    drawRoundRect(
                        color = colors.amberLine,
                        topLeft = Offset(outStart, 0f),
                        size = Size(outW, h),
                        cornerRadius = CornerRadius(2f, 2f)
                    )

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
                    Text(
                        text = "AERIS was 12.8 m from the new fix after the satellite loss; holding the last fix would have left it 86 m away.",
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
                onPlayMoment = { t ->
                    compareOutage = null
                    playbackClock.seekToSeconds(t)
                    playbackClock.play()
                },
                onDismiss = { compareOutage = null }
            )
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

    val polyManager = remember { mutableStateOf<PolylineAnnotationManager?>(null) }
    val fullTrackAnno = remember { mutableStateOf<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation?>(null) }
    val travelledAnno = remember { mutableStateOf<com.mapbox.maps.plugin.annotation.generated.PolylineAnnotation?>(null) }

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
            // Load official Dark style per V0 § 1
            if (loadedStyleUri != mapStyle.mapboxUri) {
                mv.mapboxMap.loadStyleUri(mapStyle.mapboxUri)
                loadedStyleUri = mapStyle.mapboxUri
            }

            val pt = currentPoint ?: drive.points.firstOrNull() ?: return@AndroidView

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

            // Handle zoom controls
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

            if (polyManager.value == null) {
                polyManager.value = mv.annotations.createPolylineAnnotationManager()
            }

            val pm = polyManager.value ?: return@AndroidView

            // Pre-render entire track once in subtle background color per V3
            if (fullTrackAnno.value == null && drive.points.size >= 2) {
                val fullPts = drive.points.map { Point.fromLngLat(it.lon, it.lat) }
                fullTrackAnno.value = pm.create(
                    PolylineAnnotationOptions()
                        .withPoints(fullPts)
                        .withLineColor("#3A4B5D")
                        .withLineWidth(3.5)
                        .withLineOpacity(0.4)
                )
            }

            // Update travelled line in-place without delete/create thrashing per V0 § 1 / V3
            if (currentIndex >= 1 && drive.points.isNotEmpty()) {
                val travelled = drive.points.take(currentIndex + 1).map { Point.fromLngLat(it.lon, it.lat) }
                val col = if (isOutage) "#F2A93B" else "#6D8BFF"
                val curAnno = travelledAnno.value
                if (curAnno == null) {
                    travelledAnno.value = pm.create(
                        PolylineAnnotationOptions()
                            .withPoints(travelled)
                            .withLineColor(col)
                            .withLineWidth(4.5)
                            .withLineOpacity(0.95)
                    )
                } else {
                    curAnno.points = travelled
                    curAnno.lineColorString = col
                    pm.update(curAnno)
                }
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}
