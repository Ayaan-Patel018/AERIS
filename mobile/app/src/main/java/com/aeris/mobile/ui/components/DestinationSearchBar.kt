package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Search
import androidx.compose.ui.draw.rotate
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.ui.screen.GeocoderResult
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey15
import com.aeris.mobile.ui.theme.AerisGrey30
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70

// RouteInputPanel - Google-Maps style 2-field origin + destination UI

@Composable
fun RouteInputPanel(
    originQuery: String,
    originResults: List<GeocoderResult>,
    isOriginLoading: Boolean,
    originName: String?,
    onOriginQueryChange: (String) -> Unit,
    onOriginSelected: (GeocoderResult) -> Unit,
    onOriginClear: () -> Unit,
    destQuery: String,
    destResults: List<GeocoderResult>,
    isDestLoading: Boolean,
    hasDestination: Boolean,
    destinationName: String?,
    onDestQueryChange: (String) -> Unit,
    onDestSelected: (GeocoderResult) -> Unit,
    onDestClear: () -> Unit,
    onSwap: () -> Unit,
    isNavigating: Boolean,
    isExpanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val focusManager = LocalFocusManager.current
    var originFocused by remember { mutableStateOf(false) }
    var destFocused by remember { mutableStateOf(false) }

    // Glassmorphism modifier
    val glassModifier = Modifier
        .clip(RoundedCornerShape(24.dp))
        .background(Color(0x22FFFFFF))
        .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(24.dp))

    if (isNavigating && hasDestination) {
        Row(
            modifier = modifier
                .fillMaxWidth()
                .then(glassModifier)
                .padding(horizontal = 16.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(Color(0xFF4A90D9)))
            Spacer(Modifier.width(8.dp))
            Text(
                text = destinationName?.split(",")?.first()?.trim() ?: "",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.weight(1f),
            )
            Box(
                modifier = Modifier.size(26.dp).clip(CircleShape).background(Color(0x33FFFFFF))
                    .clickable { onDestClear(); focusManager.clearFocus() },
                contentAlignment = Alignment.Center,
            ) {
                Icon(imageVector = Icons.Default.Clear, contentDescription = "Cancel", tint = Color.White, modifier = Modifier.size(13.dp))
            }
        }
        return
    }

    if (!isExpanded) {
        // Collapsed Simple Search Button
        Row(
            modifier = modifier
                .fillMaxWidth()
                .then(glassModifier)
                .clickable { onExpandedChange(true) }
                .padding(horizontal = 18.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(imageVector = Icons.Default.Search, contentDescription = null, tint = Color.White, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(12.dp))
            Text(
                text = "Where to?",
                style = MaterialTheme.typography.bodyLarge,
                color = Color.White,
                fontWeight = FontWeight.Medium,
            )
        }
        return
    }

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth()
                .then(glassModifier)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Back button to close search
            Box(
                modifier = Modifier.size(32.dp).clip(CircleShape).clickable { onExpandedChange(false); focusManager.clearFocus() },
                contentAlignment = Alignment.Center
            ) {
                Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(8.dp))
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(20.dp)) {
                Box(modifier = Modifier.size(10.dp).clip(CircleShape).border(2.dp, Color(0xFF4A90D9), CircleShape))
                repeat(3) {
                    Spacer(Modifier.height(3.dp))
                    Box(modifier = Modifier.size(2.dp).clip(CircleShape).background(Color(0x88FFFFFF)))
                }
                Spacer(Modifier.height(3.dp))
                Box(modifier = Modifier.size(10.dp).clip(CircleShape).background(Color(0xFFE53935)))
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                RouteSearchField(
                    value = originQuery,
                    onValueChange = onOriginQueryChange,
                    placeholder = originName ?: "Current Location",
                    isLoading = isOriginLoading,
                    isFocused = originFocused,
                    onFocusChange = { originFocused = it },
                    onSearch = { focusManager.clearFocus() },
                    showClear = originQuery.isNotEmpty() || originName != null,
                    onClear = { onOriginClear(); focusManager.clearFocus() },
                )
                Box(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp).height(0.5.dp).background(Color(0x33FFFFFF)))
                RouteSearchField(
                    value = destQuery,
                    onValueChange = onDestQueryChange,
                    placeholder = if (hasDestination && destinationName != null) destinationName.split(",").first().trim() else "Where to?",
                    isLoading = isDestLoading,
                    isFocused = destFocused,
                    onFocusChange = { destFocused = it },
                    onSearch = { focusManager.clearFocus() },
                    showClear = hasDestination || destQuery.isNotEmpty(),
                    onClear = { onDestClear(); focusManager.clearFocus() },
                )
            }
            Spacer(Modifier.width(10.dp))
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(Color(0x33FFFFFF))
                    .clickable(onClick = onSwap),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowForward,
                    contentDescription = "Swap origin and destination",
                    tint = Color.White,
                    modifier = Modifier.size(16.dp).rotate(90f),
                )
            }
        }
        AnimatedVisibility(visible = originResults.isNotEmpty() && originFocused, enter = expandVertically() + fadeIn(tween(150)), exit = shrinkVertically() + fadeOut(tween(100))) {
            RouteResultsList(results = originResults, onClick = { onOriginSelected(it); focusManager.clearFocus() })
        }
        AnimatedVisibility(visible = destResults.isNotEmpty() && destFocused, enter = expandVertically() + fadeIn(tween(150)), exit = shrinkVertically() + fadeOut(tween(100))) {
            RouteResultsList(results = destResults, onClick = { onDestSelected(it); focusManager.clearFocus() })
        }
    }
}

@Composable
private fun RouteSearchField(
    value: String, onValueChange: (String) -> Unit, placeholder: String,
    isLoading: Boolean, isFocused: Boolean, onFocusChange: (Boolean) -> Unit,
    onSearch: () -> Unit, showClear: Boolean, onClear: () -> Unit,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (isLoading) CircularProgressIndicator(color = Color.White, modifier = Modifier.size(15.dp), strokeWidth = 1.5.dp)
        else Icon(imageVector = Icons.Default.Search, contentDescription = null, tint = if (isFocused) Color.White else Color(0xCCFFFFFF), modifier = Modifier.size(15.dp))
        Spacer(Modifier.width(8.dp))
        BasicTextField(
            value = value, onValueChange = onValueChange,
            modifier = Modifier.weight(1f).onFocusChanged { onFocusChange(it.isFocused) },
            textStyle = TextStyle(color = Color.White, fontSize = 14.sp, letterSpacing = 0.1.sp),
            cursorBrush = SolidColor(Color.White), singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { onSearch() }),
            decorationBox = { inner ->
                if (value.isEmpty()) Text(text = placeholder, style = MaterialTheme.typography.bodyMedium, color = AerisGrey50, fontSize = 14.sp)
                inner()
            },
        )
        if (showClear && value.isNotEmpty()) {
            Spacer(Modifier.width(6.dp))
            Box(modifier = Modifier.size(20.dp).clip(CircleShape).background(Color(0x33FFFFFF)).clickable(onClick = onClear), contentAlignment = Alignment.Center) {
                Icon(imageVector = Icons.Default.Clear, contentDescription = "Clear", tint = Color.White, modifier = Modifier.size(12.dp))
            }
        }
    }
}

@Composable
private fun RouteResultsList(results: List<GeocoderResult>, onClick: (GeocoderResult) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 5.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0x88000000))
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(16.dp)),
    ) {
        results.forEachIndexed { index, result ->
            Row(
                modifier = Modifier.fillMaxWidth().clickable { onClick(result) }.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(modifier = Modifier.size(28.dp).clip(CircleShape).background(AerisGrey15), contentAlignment = Alignment.Center) {
                    Icon(imageVector = Icons.Default.LocationOn, contentDescription = null, tint = AerisGrey70, modifier = Modifier.size(14.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    val parts = result.name.split(",")
                    Text(text = parts.firstOrNull()?.trim() ?: result.name, style = MaterialTheme.typography.bodyMedium, color = Color.White, fontWeight = FontWeight.Medium)
                    if (parts.size > 1) Text(text = parts.drop(1).joinToString(",").trim(), style = MaterialTheme.typography.labelSmall, color = AerisGrey50, maxLines = 1)
                }
            }
            if (index < results.lastIndex) Box(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).height(0.5.dp).background(Color(0x33FFFFFF)))
        }
    }
}

// DestinationSearchBar kept for backward compatibility
@Composable
fun DestinationSearchBar(
    query: String, results: List<GeocoderResult>, isLoading: Boolean,
    hasDestination: Boolean, destinationName: String?,
    onQueryChange: (String) -> Unit, onResultSelected: (GeocoderResult) -> Unit,
    onClear: () -> Unit, modifier: Modifier = Modifier,
) {
    val focusManager = LocalFocusManager.current
    var isFocused by remember { mutableStateOf(false) }
    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp))
                .background(AerisGrey10.copy(alpha = 0.96f))
                .border(width = if (isFocused) 1.dp else 0.5.dp, color = if (isFocused) Color.White.copy(alpha = 0.6f) else AerisGrey30, shape = RoundedCornerShape(28.dp))
                .padding(horizontal = 16.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (isLoading) CircularProgressIndicator(color = AerisGrey70, modifier = Modifier.size(17.dp), strokeWidth = 1.8.dp)
            else Icon(imageVector = Icons.Default.Search, contentDescription = null, tint = if (isFocused) Color.White else AerisGrey50, modifier = Modifier.size(17.dp))
            Spacer(modifier = Modifier.width(11.dp))
            BasicTextField(
                value = query, onValueChange = onQueryChange,
                modifier = Modifier.weight(1f).onFocusChanged { isFocused = it.isFocused },
                textStyle = TextStyle(color = Color.White, fontSize = 15.sp, letterSpacing = 0.1.sp),
                cursorBrush = SolidColor(Color.White), singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { focusManager.clearFocus() }),
                decorationBox = { inner ->
                    if (query.isEmpty()) Text(text = if (hasDestination && destinationName != null) destinationName.split(",").first().trim() else "Where to?", style = MaterialTheme.typography.bodyMedium, color = AerisGrey50)
                    inner()
                },
            )
            if (hasDestination || query.isNotEmpty()) {
                Spacer(modifier = Modifier.width(8.dp))
                Box(modifier = Modifier.size(26.dp).clip(CircleShape).background(AerisGrey15).clickable { onClear(); focusManager.clearFocus() }, contentAlignment = Alignment.Center) {
                    Icon(imageVector = Icons.Default.Clear, contentDescription = "Clear", tint = AerisGrey70, modifier = Modifier.size(13.dp))
                }
            }
        }
        AnimatedVisibility(visible = results.isNotEmpty() && isFocused, enter = expandVertically() + fadeIn(tween(150)), exit = shrinkVertically() + fadeOut(tween(100))) {
            Column(modifier = Modifier.fillMaxWidth().padding(top = 5.dp).clip(RoundedCornerShape(16.dp)).background(AerisGrey10.copy(alpha = 0.98f)).border(0.5.dp, AerisGrey30, RoundedCornerShape(16.dp))) {
                results.forEachIndexed { index, result ->
                    Row(modifier = Modifier.fillMaxWidth().clickable { onResultSelected(result); focusManager.clearFocus() }.padding(horizontal = 16.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(modifier = Modifier.size(30.dp).clip(CircleShape).background(AerisGrey15), contentAlignment = Alignment.Center) {
                            Icon(imageVector = Icons.Default.LocationOn, contentDescription = null, tint = AerisGrey70, modifier = Modifier.size(15.dp))
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            val parts = result.name.split(",")
                            Text(text = parts.firstOrNull()?.trim() ?: result.name, style = MaterialTheme.typography.bodyMedium, color = Color.White, fontWeight = FontWeight.Medium)
                            if (parts.size > 1) Text(text = parts.drop(1).joinToString(",").trim(), style = MaterialTheme.typography.labelSmall, color = AerisGrey50, maxLines = 1)
                        }
                    }
                    if (index < results.lastIndex) Box(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).height(0.5.dp).background(AerisGrey30))
                }
            }
        }
    }
}
