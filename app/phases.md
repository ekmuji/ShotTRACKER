# ShotTrackr — Bottom-Up Android Migration & SwishAI Integration Plan

The errors in image_62cfad.png are exactly what we expect to see at this stage.

The previous snippet provided the target ViewModel code to drive the new Compose UI, but the underlying Kotlin data classes (like WorkoutUiState, TrackingStatus, ShotResult) haven't been created yet. Furthermore, your C++ JNI bridge (FrameResult) doesn't yet output the new fields (totalShots, justMadeShot, hoopTracked) because the native C++ engine hasn't been updated to match the SwishAI physics logic.



Phase 4: Jetpack Compose UI Migration

Goal: Strip out legacy XML and implement the high-visibility, landscape-optimized UI.

1. Delete Legacy XML

Remove:

fragment_workout.xml

fragment_dashboard.xml

2. Implement CameraX in Compose (CameraPreviewLayer.kt)

Use an AndroidView to wrap the CameraX PreviewView.

Implement an ImageAnalysis.Analyzer that:

Captures camera frames.

Rotates them appropriately for landscape.

Feeds them to:
WorkoutViewModel.processFrame(bitmap)

3. Build the Live Workout Screen (WorkoutScreen.kt)

Implement:

A massive 80sp scoreboard layout.

An AnimatedVisibility overlay for the 1.5-second ✓ MADE transient indicator.

4. Implement the Bounding Box Canvas

Create a Compose Canvas above the CameraX view.

Read the scaled coordinates from ViewModel.boundingBoxes and draw the detection rectangles over the live camera feed.

Recommended Implementation Order

Start strictly with Phase 1 and Phase 2.

The dependency chain is:

YOLO11 model
↓
Detection classes
↓
Native C++ tracking / physics
↓
JNI bridge
↓
FrameResult
↓
WorkoutViewModel
↓
WorkoutUiState
↓
Jetpack Compose UI

This bottom-up approach prevents the UI from being built against unstable native APIs and data models.

Next Step

The next implementation task is to write the exact C++ TrackerEngine.h and TrackerEngine.cpp required to port the SwishAI cooldown logic into TrackerEngine.