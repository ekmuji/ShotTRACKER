package com.shottrackr.ui.workout // Moved from .data to match modern UI grouping

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shottrackr.engine.FrameResult
import com.shottrackr.engine.TrackerBridge
import com.shottrackr.ml.ShotDetector
import com.shottrackr.ml.VideoProcessor
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class WorkoutViewModel @Inject constructor(
    application: Application
) : AndroidViewModel(application) {

    private val shotDetector = ShotDetector(application)
    private val trackerBridge = TrackerBridge()

    // 1. Replaced LiveData with StateFlow for Jetpack Compose
    private val _uiState = MutableStateFlow(WorkoutUiState())
    val uiState: StateFlow<WorkoutUiState> = _uiState.asStateFlow()

    // Optional: Keep exposing raw boxes if you need a Compose Canvas to draw them
    private val _boundingBoxes = MutableStateFlow<FrameResult?>(null)
    val boundingBoxes = _boundingBoxes.asStateFlow()

    private var frameIndex = 0

    init {
        trackerBridge.create(30f)
    }

    fun processFrame(bitmap: Bitmap) {
        val detections = shotDetector.detect(bitmap)

        // 2. UPDATED CLASS IDs matching the new YOLO11 model
        // 0 = Ball, 1 = Ball in Basket, 2 = Player, 3 = Basket, 4 = Player Shooting
        val ball = detections.find { it.classId == 0 }
        val hoop = detections.find { it.classId == 3 } // Hoop is now 3!
        val ballInBasket = detections.find { it.classId == 1 }
        val playerShooting = detections.find { it.classId == 4 }

        val result = trackerBridge.update(
            timestampMs = System.currentTimeMillis(),
            ballDetected = ball != null,
            ballCx = ball?.centerX ?: 0f,
            ballCy = ball?.centerY ?: 0f,
            ballW = ball?.width ?: 0f,
            ballH = ball?.height ?: 0f,
            ballConf = ball?.confidence ?: 0f,
            hoopDetected = hoop != null,
            hoopCx = hoop?.centerX ?: 0f,
            hoopCy = hoop?.centerY ?: 0f,
            hoopW = hoop?.width ?: 0f,
            hoopH = hoop?.height ?: 0f,
            hoopConf = hoop?.confidence ?: 0f,
            ballInBasket != null ,
            playerShooting != null
        )

        result?.let { frameResult ->
            _boundingBoxes.value = frameResult

            // 3. Map C++ output to Jetpack Compose UI State
            updateComposeUiState(frameResult, ballInBasket != null)
        }
    }

    private fun updateComposeUiState(frameResult: FrameResult, swishDetectedByYolo: Boolean) {
        // Here we blend your C++ logic and YOLO classes to drive the Compose HUD.
        // Replace `frameResult.totalMakes` with whatever your C++ JNI currently returns.

        val makes = frameResult.totalMakes
        val totalShots = frameResult.totalShots
        val misses = totalShots - makes
        val percentage = if (totalShots > 0) ((makes.toFloat() / totalShots) * 100).toInt() else 0

        // Determine if we need to fire a transient animation this frame
        val latestShot = when {
            frameResult.justMadeShot || swishDetectedByYolo -> ShotResult.MADE
            frameResult.justMissedShot -> ShotResult.MISSED
            else -> null
        }

        // Determine tracking health (e.g. if C++ lost the rim)
        val status = if (frameResult.hoopTracked) TrackingStatus.TRACKING else TrackingStatus.FINDING_RIM

        _uiState.update { currentState ->
            currentState.copy(
                makes = makes,
                misses = misses,
                totalShots = totalShots,
                percentage = "$percentage%",
                trackingStatus = status,
                // Only overwrite latestShot if there's a new event, so the 1.5s animation can play out
                latestShot = latestShot ?: currentState.latestShot
            )
        }
    }

    fun resetSession() {
        trackerBridge.resetSession()
        _uiState.value = WorkoutUiState()
        frameIndex = 0
    }

    override fun onCleared() {
        super.onCleared()
        shotDetector.close()
        trackerBridge.destroy()
    }

    // (processVideoFile remains largely the same, just updating StateFlow instead of LiveData)
    fun processVideoFile(videoUri: Uri, videoProcessor: VideoProcessor) {
        viewModelScope.launch {
            var frameIndex = 0

            videoProcessor.analyzeVideo(videoUri) { detections ->

                val ball = detections.find { it.classId == 0 }
                val hoop = detections.find { it.classId == 3 } // Class 3 is Basket
                val ballInBasket = detections.find { it.classId == 1 } // Class 1
                val playerShooting = detections.find { it.classId == 4 } // Class 4

                // Simulate timestamps for the C++ engine (assume 30fps = ~33ms per frame)
                val simulatedTimeMs = frameIndex * 33L

                val result = trackerBridge.update(
                    timestampMs = simulatedTimeMs,
                    ballDetected = ball != null,
                    ballCx = ball?.centerX ?: 0f, ballCy = ball?.centerY ?: 0f,
                    ballW = ball?.width ?: 0f, ballH = ball?.height ?: 0f, ballConf = ball?.confidence ?: 0f,
                    hoopDetected = hoop != null,
                    hoopCx = hoop?.centerX ?: 0f, hoopCy = hoop?.centerY ?: 0f,
                    hoopW = hoop?.width ?: 0f, hoopH = hoop?.height ?: 0f, hoopConf = hoop?.confidence ?: 0f,
                    ballInBasketDetected = ballInBasket != null,
                    playerShootingDetected = playerShooting != null
                )

                result?.let { frameResult ->
                    _boundingBoxes.value = frameResult
                    updateComposeUiState(frameResult, ballInBasket != null)
                }

                frameIndex++
            }
        }
    }
}