package com.aeris.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.aeris.mobile.domain.adapter.BundledTripLoader
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.playback.PlaybackClock
import com.aeris.mobile.domain.routing.RouteOption
import com.aeris.mobile.domain.search.SearchPlace
import com.aeris.mobile.ui.components.AerisNavTab
import com.aeris.mobile.ui.screen.DashModeScreen
import com.aeris.mobile.ui.screen.ExploreScreen
import com.aeris.mobile.ui.screen.LoadingScreen
import com.aeris.mobile.ui.screen.LoadingStage
import com.aeris.mobile.ui.screen.NavigationScreen
import com.aeris.mobile.ui.screen.OnboardingScreen
import com.aeris.mobile.ui.screen.RecordScreen
import com.aeris.mobile.ui.screen.ReplayScreen
import com.aeris.mobile.ui.screen.RoutePreviewScreen
import com.aeris.mobile.ui.screen.SearchOverlay
import com.aeris.mobile.ui.screen.SettingsDialog
import com.aeris.mobile.ui.screen.StageStatus
import com.aeris.mobile.ui.screen.TripDetailScreen
import com.aeris.mobile.ui.screen.TripsScreen
import com.aeris.mobile.ui.theme.AERISTheme
import kotlinx.coroutines.delay

/**
 * Main entry point of the AERIS Mobile Application.
 *
 * Implements R1–R6 Architecture:
 * - Direct landing into Explore Screen (Mockup 00 Screen 1) instead of video scrubber.
 * - Complete 6-screen navigation flow:
 *   1. Explore (home)
 *   2. Search (fullscreen grouped)
 *   3. Route Preview (Day theme, alternatives, satellite warnings)
 *   4. Navigating (turn banner, speed bubble, bottom bar)
 *   5. Trip Playback (honesty chip, outage banner, readouts, moments carousel, distance rail)
 *   6. Trip Detail (facts row, moments list, Play trip action)
 */
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        if (BuildConfig.MAPBOX_PUBLIC_TOKEN.isNotEmpty()) {
            com.mapbox.common.MapboxOptions.accessToken = BuildConfig.MAPBOX_PUBLIC_TOKEN
        }

        setContent {
            val systemDark = isSystemInDarkTheme()
            var isNightTheme by remember { mutableStateOf(systemDark) }

            AERISTheme(darkTheme = isNightTheme) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AerisApp(
                        isNightTheme = isNightTheme,
                        onToggleNightTheme = { isNightTheme = it }
                    )
                }
            }
        }
    }
}

@Composable
fun AerisApp(
    isNightTheme: Boolean,
    onToggleNightTheme: (Boolean) -> Unit,
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val navController = rememberNavController()
    val scope = rememberCoroutineScope()

    var loadedDrive by remember { mutableStateOf<Drive?>(null) }
    var selectedDriveForDetail by remember { mutableStateOf<Drive?>(null) }
    var selectedPlaceForRouting by remember { mutableStateOf<SearchPlace?>(null) }
    var selectedRouteForNav by remember { mutableStateOf<RouteOption?>(null) }

    var loadError by remember { mutableStateOf<String?>(null) }
    val playbackClock = remember { PlaybackClock(scope) }
    var showSettingsDialog by remember { mutableStateOf(false) }

    var stages by remember {
        mutableStateOf(
            listOf(
                LoadingStage("Reading drive data", StageStatus.ACTIVE),
                LoadingStage("Preparing the map", StageStatus.PENDING),
                LoadingStage("Building the path", StageStatus.PENDING)
            )
        )
    }

    // Load drive on start
    LaunchedEffect(Unit) {
        try {
            stages = listOf(
                LoadingStage("Reading drive data", StageStatus.ACTIVE),
                LoadingStage("Preparing the map", StageStatus.PENDING),
                LoadingStage("Building the path", StageStatus.PENDING)
            )

            val drive = BundledTripLoader.load(context)

            stages = listOf(
                LoadingStage("Reading drive data", StageStatus.DONE),
                LoadingStage("Preparing the map", StageStatus.ACTIVE),
                LoadingStage("Building the path", StageStatus.PENDING)
            )
            delay(120L)

            stages = listOf(
                LoadingStage("Reading drive data", StageStatus.DONE),
                LoadingStage("Preparing the map", StageStatus.DONE),
                LoadingStage("Building the path", StageStatus.ACTIVE)
            )
            delay(100L)

            stages = listOf(
                LoadingStage("Reading drive data", StageStatus.DONE),
                LoadingStage("Preparing the map", StageStatus.DONE),
                LoadingStage("Building the path", StageStatus.DONE)
            )

            loadedDrive = drive
            selectedDriveForDetail = drive
            playbackClock.attachDrive(drive)

            // Navigate to Explore (home screen per R1 § 3)
            navController.navigate("explore") {
                popUpTo("loading") { inclusive = true }
            }
        } catch (e: Exception) {
            loadError = "Failed to load drive: ${e.message}"
            stages = stages.map { LoadingStage(it.label, StageStatus.FAILED) }
        }
    }

    NavHost(
        navController = navController,
        startDestination = "loading"
    ) {
        composable("loading") {
            LoadingScreen(
                stages = stages,
                driveId = loadedDrive?.meta?.id ?: "S3b",
                errorMessage = loadError,
                onRetry = {
                    loadError = null
                }
            )
        }

        composable("onboarding") {
            OnboardingScreen(
                onFinished = {
                    navController.navigate("explore") {
                        popUpTo("onboarding") { inclusive = true }
                    }
                }
            )
        }

        // Screen 1: Explore (Home)
        composable("explore") {
            val d = loadedDrive
            if (d != null) {
                ExploreScreen(
                    bundledDrive = d,
                    isNightTheme = isNightTheme,
                    onOpenSearch = {
                        navController.navigate("search")
                    },
                    onOpenSettings = {
                        showSettingsDialog = true
                    },
                    onSelectDrive = { selected ->
                        selectedDriveForDetail = selected
                        navController.navigate("trip_detail")
                    },
                    onNavigateTab = { tab ->
                        when (tab) {
                            AerisNavTab.EXPLORE -> {}
                            AerisNavTab.TRIPS -> navController.navigate("trips")
                            AerisNavTab.RECORD -> navController.navigate("record")
                        }
                    }
                )
            } else {
                LoadingScreen(stages = stages, driveId = "S3b", errorMessage = loadError)
            }
        }

        // Screen 2: Search Surface
        composable("search") {
            val dList = listOfNotNull(loadedDrive)
            SearchOverlay(
                drives = dList,
                onSelectPlace = { place ->
                    selectedPlaceForRouting = place
                    navController.navigate("route_preview")
                },
                onSelectDrive = { selected ->
                    selectedDriveForDetail = selected
                    navController.navigate("trip_detail")
                },
                onSelectMoment = { moment ->
                    loadedDrive?.let { d ->
                        playbackClock.attachDrive(d)
                        playbackClock.seekToSeconds(moment.timestampSec)
                        navController.navigate("replay")
                    }
                },
                onDismiss = { navController.popBackStack() }
            )
        }

        // Screen 3: Route Preview (Day Theme)
        composable("route_preview") {
            val place = selectedPlaceForRouting ?: SearchPlace("Millbrook Park", "Park", "Northgate", 52.375, -1.258)
            RoutePreviewScreen(
                destinationName = place.name,
                toLat = place.lat,
                toLon = place.lon,
                onStartNavigation = { route ->
                    selectedRouteForNav = route
                    navController.navigate("navigation")
                },
                onBack = { navController.popBackStack() }
            )
        }

        // Screen 4: Turn-by-Turn Navigating
        composable("navigation") {
            val route = selectedRouteForNav ?: com.aeris.mobile.domain.routing.RouteOption(
                id = "route_active",
                durationMinutes = 18,
                distanceKm = 6.2,
                label = "Fastest route",
                points = emptyList()
            )
            NavigationScreen(
                route = route,
                destinationName = selectedPlaceForRouting?.name ?: "Millbrook Park",
                isNightTheme = isNightTheme,
                onEndNavigation = {
                    navController.popBackStack("explore", inclusive = false)
                }
            )
        }

        // Screen 5: Trip Playback
        composable("replay") {
            val d = selectedDriveForDetail ?: loadedDrive
            if (d != null) {
                ReplayScreen(
                    drive = d,
                    playbackClock = playbackClock,
                    isNightTheme = isNightTheme,
                    onToggleNightTheme = onToggleNightTheme,
                    onBack = { navController.popBackStack() },
                    onOpenDashView = { navController.navigate("dash") },
                    onOpenRecordMode = {
                        navController.navigate("record")
                    }
                )
            } else {
                LoadingScreen(stages = stages, driveId = "S3b", errorMessage = loadError)
            }
        }

        // Dash Mode Screen (glanceable in-car view per R5 § 4)
        composable("dash") {
            val d = selectedDriveForDetail ?: loadedDrive
            val pt by playbackClock.currentPoint.collectAsState()
            val frac by playbackClock.currentFraction.collectAsState()
            val playing by playbackClock.isPlaying.collectAsState()
            DashModeScreen(
                currentPoint = pt,
                currentFraction = frac,
                durationSec = d?.meta?.durationSec ?: 681.0,
                isPlaying = playing,
                driveId = d?.meta?.id ?: "S3b",
                onTogglePlayPause = { playbackClock.togglePlayPause() },
                onExitDashMode = { navController.popBackStack() }
            )
        }

        // Trips Tab: Collection of recorded drives per R5 § 1
        composable("trips") {
            val dList = listOfNotNull(loadedDrive)
            TripsScreen(
                drives = dList,
                onSelectDrive = { selected ->
                    selectedDriveForDetail = selected
                    navController.navigate("trip_detail")
                },
                onOpenSearch = { navController.navigate("search") },
                onOpenSettings = { showSettingsDialog = true },
                onOpenRecord = { navController.navigate("record") },
                onNavigateTab = { tab ->
                    when (tab) {
                        AerisNavTab.EXPLORE -> navController.navigate("explore")
                        AerisNavTab.TRIPS -> {}
                        AerisNavTab.RECORD -> navController.navigate("record")
                    }
                }
            )
        }

        // Screen 6: Trip Detail
        composable("trip_detail") {
            val d = selectedDriveForDetail ?: loadedDrive
            if (d != null) {
                TripDetailScreen(
                    drive = d,
                    onPlayTrip = {
                        playbackClock.attachDrive(d)
                        playbackClock.seekToFraction(0f)
                        playbackClock.play()
                        navController.navigate("replay")
                    },
                    onPlayAtTimestamp = { t ->
                        playbackClock.attachDrive(d)
                        playbackClock.seekToSeconds(t)
                        playbackClock.play()
                        navController.navigate("replay")
                    },
                    onBack = {
                        navController.popBackStack()
                    },
                    onNavigateTab = { tab ->
                        when (tab) {
                            AerisNavTab.EXPLORE -> navController.navigate("explore")
                            AerisNavTab.TRIPS -> navController.navigate("trips")
                            AerisNavTab.RECORD -> navController.navigate("record")
                        }
                    }
                )
            }
        }

        // Record Screen
        composable("record") {
            RecordScreen(
                onNavigateBack = { navController.popBackStack() },
                onNavigateTab = { tab ->
                    when (tab) {
                        AerisNavTab.EXPLORE -> navController.navigate("explore")
                        AerisNavTab.TRIPS -> navController.navigate("trips")
                        AerisNavTab.RECORD -> {}
                    }
                }
            )
        }
    }

    if (showSettingsDialog) {
        SettingsDialog(
            isNightTheme = isNightTheme,
            onToggleNightTheme = onToggleNightTheme,
            use95PercentUncertainty = false,
            onToggle95Percent = {},
            showReferenceTrack = false,
            onToggleReferenceTrack = {},
            useMpsUnits = false,
            onToggleUnits = {},
            onDismiss = { showSettingsDialog = false }
        )
    }
}
