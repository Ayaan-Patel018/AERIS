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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.search.SearchDriveResult
import com.aeris.mobile.domain.search.SearchMomentResult
import com.aeris.mobile.domain.search.SearchPlace
import com.aeris.mobile.domain.search.SearchService
import com.aeris.mobile.ui.theme.Aeris
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Fullscreen Search Surface matching Mockup 00 Screen 2 & R3 § 2.
 *
 * Grouped sections (Places, Drives, Moments), scope filters, debounced Photon typeahead.
 */
@Composable
fun SearchOverlay(
    drives: List<Drive>,
    onSelectPlace: (SearchPlace) -> Unit,
    onSelectDrive: (Drive) -> Unit,
    onSelectMoment: (SearchMomentResult) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors
    val scope = rememberCoroutineScope()

    var query by remember { mutableStateOf("") }
    var selectedScope by remember { mutableStateOf("All") }

    var places by remember { mutableStateOf<List<SearchPlace>>(emptyList()) }
    var driveResults by remember { mutableStateOf<List<SearchDriveResult>>(emptyList()) }
    var momentResults by remember { mutableStateOf<List<SearchMomentResult>>(emptyList()) }
    var isLoadingPlaces by remember { mutableStateOf(false) }

    val focusRequester = remember { FocusRequester() }
    var debounceJob by remember { mutableStateOf<Job?>(null) }

    // Instant local search for drives and moments
    LaunchedEffect(query) {
        driveResults = if (query.isNotBlank()) SearchService.searchLocalDrives(query, drives) else emptyList()
        momentResults = if (query.isNotBlank()) SearchService.searchLocalMoments(query, drives) else emptyList()

        // Debounce 300 ms for Photon remote places per R3 § 2
        debounceJob?.cancel()
        if (query.trim().length >= 3) {
            isLoadingPlaces = true
            debounceJob = scope.launch {
                delay(300L)
                places = SearchService.searchPlaces(query.trim())
                isLoadingPlaces = false
            }
        } else {
            places = if (query.trim().isEmpty()) {
                getPreloadedSuggestions()
            } else {
                emptyList()
            }
            isLoadingPlaces = false
        }
    }

    LaunchedEffect(Unit) {
        focusRequester.requestFocus()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.paper)
            .statusBarsPadding()
    ) {
        // Top search bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Back button
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .clickable(role = Role.Button, onClick = onDismiss)
                    .semantics {
                        role = Role.Button
                        contentDescription = "Back to map"
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = null,
                    tint = colors.ink,
                    modifier = Modifier.size(22.dp)
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            // Search input field with clear button
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(44.dp)
                    .clip(RoundedCornerShape(22.dp))
                    .background(colors.chalk)
                    .padding(horizontal = 16.dp),
                contentAlignment = Alignment.CenterStart
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    BasicTextField(
                        value = query,
                        onValueChange = { query = it },
                        modifier = Modifier
                            .weight(1f)
                            .focusRequester(focusRequester),
                        textStyle = TextStyle(
                            color = colors.ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium
                        ),
                        singleLine = true,
                        cursorBrush = SolidColor(colors.cobalt),
                        decorationBox = { innerTextField ->
                            if (query.isEmpty()) {
                                Text(
                                    text = "Search places or drives",
                                    color = colors.ink3,
                                    fontSize = 15.sp,
                                )
                            }
                            innerTextField()
                        }
                    )

                    if (query.isNotEmpty()) {
                        Box(
                            modifier = Modifier
                                .size(24.dp)
                                .clip(CircleShape)
                                .clickable { query = "" },
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Clear,
                                contentDescription = "Clear text",
                                tint = colors.ink3,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }

        // Scope filter chips: All, Places, Drives, Moments
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("All", "Places", "Drives", "Moments").forEach { scopeLabel ->
                val isSelected = selectedScope == scopeLabel
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(if (isSelected) colors.cobaltSoft else colors.paper)
                        .border(
                            1.dp,
                            if (isSelected) colors.cobalt else colors.harbor,
                            RoundedCornerShape(16.dp)
                        )
                        .clickable { selectedScope = scopeLabel }
                        .padding(horizontal = 14.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = scopeLabel,
                        color = if (isSelected) colors.cobalt else colors.ink2,
                        fontSize = 12.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Grouped Results List
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
        ) {
            // Section 1: Places
            if ((selectedScope == "All" || selectedScope == "Places") && places.isNotEmpty()) {
                item {
                    SectionHeader(title = "Places")
                }
                items(places) { place ->
                    PlaceResultRow(
                        place = place,
                        onClick = { onSelectPlace(place) }
                    )
                }
            }

            // Section 2: Drives
            if ((selectedScope == "All" || selectedScope == "Drives") && driveResults.isNotEmpty()) {
                item {
                    SectionHeader(title = "Drives")
                }
                items(driveResults) { driveRes ->
                    DriveResultRow(
                        result = driveRes,
                        onClick = { onSelectDrive(driveRes.drive) }
                    )
                }
            }

            // Section 3: Moments
            if ((selectedScope == "All" || selectedScope == "Moments") && momentResults.isNotEmpty()) {
                item {
                    SectionHeader(title = "Moments")
                }
                items(momentResults) { momentRes ->
                    MomentResultRow(
                        result = momentRes,
                        onClick = { onSelectMoment(momentRes) }
                    )
                }
            }
        }

        // Footer note per R3 § 2
        Text(
            text = "Places from OpenStreetMap contributors. Search text is sent to the place-search service only while you type.",
            color = colors.ink3,
            fontSize = 11.sp,
            lineHeight = 15.sp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 12.dp)
        )
    }
}

@Composable
private fun SectionHeader(title: String) {
    val colors = Aeris.colors
    Text(
        text = title,
        color = colors.ink2,
        fontSize = 13.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier.padding(top = 12.dp, bottom = 6.dp)
    )
}

@Composable
private fun PlaceResultRow(place: SearchPlace, onClick: () -> Unit) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(colors.harbor2),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.LocationOn,
                contentDescription = null,
                tint = colors.ink,
                modifier = Modifier.size(18.dp)
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = place.name,
                color = colors.ink,
                fontSize = 14.5.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(2.dp))
            val detail = if (place.distanceKm != null) {
                "${place.category} • ${String.format(java.util.Locale.getDefault(), "%.1f km away", place.distanceKm)}"
            } else {
                "${place.category} • ${place.locality}"
            }
            Text(
                text = detail,
                color = colors.ink2,
                fontSize = 12.sp,
            )
        }
    }
}

@Composable
private fun DriveResultRow(result: SearchDriveResult, onClick: () -> Unit) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(colors.cobaltSoft),
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .size(16.dp)
                    .border(2.dp, colors.cobalt, CircleShape)
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = result.label,
                color = colors.ink,
                fontSize = 14.5.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = result.summary,
                color = colors.ink2,
                fontSize = 12.sp,
            )
        }
    }
}

@Composable
private fun MomentResultRow(result: SearchMomentResult, onClick: () -> Unit) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(if (result.isOutage) colors.amberSoft else colors.harbor2),
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(if (result.isOutage) colors.amberLine else colors.ink)
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = result.title,
                color = colors.ink,
                fontSize = 14.5.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = result.detail,
                color = if (result.isOutage) colors.amberLine else colors.ink2,
                fontSize = 12.sp,
            )
        }
    }
}

private fun getPreloadedSuggestions() = listOf(
    SearchPlace("Millbrook Park", "Park", "Northgate", 52.375, -1.258, 1.2),
    SearchPlace("Mill Road Fuel Station", "Fuel", "Old Town", 52.381, -1.265, 1.8),
    SearchPlace("Millennium Hall", "Event venue", "Old Town", 52.386, -1.270, 2.4)
)
