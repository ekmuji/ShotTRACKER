package com.shottrackr.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shottrackr.ui.theme.BasketballOrange
import com.shottrackr.ui.theme.NeonGreen
import com.shottrackr.ui.theme.ShotTrackrTheme

data class WorkoutSession(
    val id: String,
    val dateText: String,     // e.g., "Oct 24, 2024  4:00 PM"
    val durationText: String, // e.g., "45m 12s"
    val streakText: String,   // e.g., "🔥 Streak: 5"
    val percentageText: String, // e.g., "45.5%"
    val makesText: String      // e.g., "45/100"
)

@Composable
fun WorkoutSessionCard(
    session: WorkoutSession,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = MaterialTheme.shapes.medium
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Left Column: Date, Duration, Streak
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = session.dateText,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.White
                )
                Text(
                    text = session.durationText,
                    fontSize = 15.sp,
                    color = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.padding(top = 2.dp)
                )
                Text(
                    text = session.streakText,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium,
                    color = NeonGreen,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }

            // Right Column: Accuracy & Makes
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = session.percentageText,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = BasketballOrange
                )
                Text(
                    text = session.makesText,
                    fontSize = 15.sp,
                    color = Color.LightGray
                )
            }
        }
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF0F1115)
@Composable
fun WorkoutSessionCardPreview() {
    ShotTrackrTheme {
        WorkoutSessionCard(
            session = WorkoutSession(
                id = "1",
                dateText = "Oct 24, 2024  4:00 PM",
                durationText = "45m 12s",
                streakText = "🔥 Streak: 8",
                percentageText = "72.0%",
                makesText = "72/100"
            )
        )
    }
}