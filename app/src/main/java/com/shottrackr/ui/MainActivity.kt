package com.shottrackr.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shottrackr.ui.components.WorkoutSession
import com.shottrackr.ui.components.WorkoutSessionCard
import com.shottrackr.ui.theme.BasketballOrange
import com.shottrackr.ui.theme.ShotTrackrTheme
import com.shottrackr.ui.workout.WorkoutScreen
import com.shottrackr.ui.workout.WorkoutViewModel
import dagger.hilt.android.AndroidEntryPoint
/**
 * MainActivity.kt

 * The main entry point of the app.
 * Marked with @AndroidEntryPoint to allow Hilt to inject dependencies.
 * Extends AppCompatActivity to support hosting Fragments (Home, Workout, Stats).
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val viewModel: WorkoutViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            ShotTrackrTheme {
                MainAppScreen(viewModel = viewModel)
            }
        }
    }
}

enum class NavigationDestination(val label: String) {
    HOME("Home"),
    WORKOUT("Workout"),
    HISTORY("History")
}

@Composable
fun MainAppScreen(viewModel: WorkoutViewModel) {
    var currentDestination by remember { mutableStateOf(NavigationDestination.HOME) }
    val uiState by viewModel.uiState.collectAsState()
    val boundingBoxes by viewModel.boundingBoxes.collectAsState()

    Scaffold(
        bottomBar = {
            // Only show bottom navigation when NOT in active workout screen
            if (currentDestination != NavigationDestination.WORKOUT) {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                    NavigationBarItem(
                        selected = currentDestination == NavigationDestination.HOME,
                        onClick = { currentDestination = NavigationDestination.HOME },
                        icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                        label = { Text("Home") }
                    )
                    NavigationBarItem(
                        selected = currentDestination == NavigationDestination.WORKOUT,
                        onClick = { currentDestination = NavigationDestination.WORKOUT },
                        icon = { Icon(Icons.Default.PlayArrow, contentDescription = "Workout") },
                        label = { Text("Workout") }
                    )
                    NavigationBarItem(
                        selected = currentDestination == NavigationDestination.HISTORY,
                        onClick = { currentDestination = NavigationDestination.HISTORY },
                        icon = { Icon(Icons.Default.Star, contentDescription = "History") },
                        label = { Text("History") }
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues)) {
            when (currentDestination) {
                NavigationDestination.HOME -> HomeScreen(onStartWorkout = {
                    currentDestination = NavigationDestination.WORKOUT
                })
                NavigationDestination.WORKOUT -> WorkoutScreen(
                    uiState = uiState,
                    frameResult = boundingBoxes,
                    onFrameCaptured = { bitmap -> viewModel.processFrame(bitmap) }
                )
                NavigationDestination.HISTORY -> HistoryScreen()
            }
        }
    }
}


@Composable
fun HomeScreen(onStartWorkout: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("ShotTrackr", fontSize = 36.sp, fontWeight = FontWeight.Black, color = BasketballOrange)
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = onStartWorkout,
            colors = ButtonDefaults.buttonColors(containerColor = BasketballOrange),
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text("START WORKOUT", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
    }
}

@Preview
@Composable
fun HistoryScreen() {
    // Dummy session data matching your previous XML layout
    val dummySessions = remember {
        listOf(
            WorkoutSession("1", "Today  4:00 PM", "45m 12s", "🔥 Streak: 8", "72.0%", "72/100"),
            WorkoutSession("2", "Yesterday  5:30 PM", "30m 00s", "🔥 Streak: 5", "66.0%", "33/50"),
            WorkoutSession("3", "Oct 18, 2024  2:15 PM", "1h 05m", "🔥 Streak: 12", "71.4%", "100/140")
        )
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 16.dp)
    ) {
        items(dummySessions) { session ->
            WorkoutSessionCard(session = session)
        }
    }
}

// --- COMPOSE PREVIEWS ---

// 1. Preview for the Home Screen
@Preview(showBackground = true, backgroundColor = 0xFF0F1115)
@Composable
fun HomeScreenPreview() {
    ShotTrackrTheme {
        // Pass an empty lambda {} so the preview doesn't crash
        HomeScreen(onStartWorkout = {})
    }
}

// 2. Preview for the History Screen
@Preview(showBackground = true, backgroundColor = 0xFF0F1115)
@Composable
fun HistoryScreenPreview() {
    ShotTrackrTheme {
        HistoryScreen()
    }
}
