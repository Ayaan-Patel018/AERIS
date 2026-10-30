package com.aeris.mobile.ui.sheet

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.search.SearchPlace
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters

/**
 * Place Sheet matching R3 § 4.
 *
 * Appears when selecting a place or long-pressing on the map.
 * Contains name, coordinates copy, distance, Directions, Save, and Share buttons.
 */
@Composable
fun PlaceSheet(
    place: SearchPlace,
    onDirectionsClick: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = Aeris.colors

    var isSaved by remember { mutableStateOf(false) }

    val coordString = String.format(java.util.Locale.getDefault(), "%.5f, %.5f", place.lat, place.lon)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
            .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
            .padding(horizontal = 24.dp, vertical = 20.dp)
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

        Spacer(modifier = Modifier.height(16.dp))

        // Title: Place Name
        Text(
            text = place.name,
            color = colors.ink,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
        )

        Spacer(modifier = Modifier.height(4.dp))

        // Category & Locality
        Text(
            text = "${place.category} • ${place.locality}",
            color = colors.ink2,
            fontSize = 13.5.sp,
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Coordinates with Copy action
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clip(RoundedCornerShape(6.dp))
                .clickable {
                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("Coordinates", coordString))
                    Toast.makeText(context, "Coordinates copied", Toast.LENGTH_SHORT).show()
                }
                .padding(vertical = 4.dp)
        ) {
            Text(
                text = coordString,
                color = colors.ink3,
                fontSize = 12.sp,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Copy",
                color = colors.cobalt,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Action Buttons Row per R3 § 4:
        // Primary filled "Directions", Tonal "Save place", Text "Share"
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Directions Button
            Button(
                onClick = onDirectionsClick,
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.ink,
                    contentColor = colors.paper
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .weight(1.5f)
                    .height(48.dp)
            ) {
                Text(
                    text = "Directions",
                    fontSize = 14.5.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }

            // Save Place Button
            OutlinedButton(
                onClick = { isSaved = !isSaved },
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = colors.ink
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .weight(1.2f)
                    .height(48.dp)
            ) {
                Text(
                    text = if (isSaved) "Saved" else "Save place",
                    fontSize = 13.5.sp,
                    fontWeight = FontWeight.Medium
                )
            }

            // Share Button
            OutlinedButton(
                onClick = {
                    val geoUri = Uri.parse("geo:${place.lat},${place.lon}?q=${Uri.encode(place.name)}")
                    val intent = Intent(Intent.ACTION_VIEW, geoUri)
                    context.startActivity(Intent.createChooser(intent, "Share place"))
                },
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = colors.ink2
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .weight(0.9f)
                    .height(48.dp)
            ) {
                Text(
                    text = "Share",
                    fontSize = 13.sp,
                )
            }
        }
    }
}
