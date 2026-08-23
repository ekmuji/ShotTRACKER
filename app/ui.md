# ShotTrackr UI Implementation Guide

## 1. Core Design Principles
*   **Design System:** Material Design 3 (MD3) with Jetpack Compose.
*   **Theme:** Dark mode default to reduce battery consumption, minimize glare, and prioritize camera feed visibility.
*   **Orientation:** Portrait for navigation and statistics; locked Landscape for the live workout tracking.
*   **Glanceability:** UI designed to be readable from 15-20 feet away during active use.

## 2. Color Palette & Typography
Use standard Android fonts (Roboto/Google Sans) with extreme scaling for live metrics (up to 80sp).

| Element | Color | Hex Code | Usage |
| :--- | :--- | :--- | :--- |
| **Background** | Deep Charcoal | `#0F1115` | App background, prevents glare. |
| **Surface** | Dark Grey | `#181B21` | Elevated cards, menus, bottom nav. |
| **Primary** | Basketball Orange | `#FF8A3D` | Primary CTAs (Start Workout), FG%. |
| **Success** | Neon Green | `#4ADE80` | Made shots, positive progress. |
| **Text (Primary)** | Off-White | `#F5F5F5` | Main numbers, active text. |
| **Text (Secondary)**| Muted Grey | `#A7ABB4` | Labels, historical metadata. |

## 3. Architecture: Unidirectional Data Flow (UDF)
The UI remains strictly separated from the YOLO11 computer vision engine.

1.  **CameraX** feeds frames to `VisionProcessor`.
2.  `VisionProcessor` runs TFLite inference.
3.  `ShotTracker` applies spatial logic to output `ShotResult.MADE` or `ShotResult.MISSED`.
4.  `WorkoutViewModel` updates internal state (makes, misses, percentage).
5.  **Jetpack Compose UI** observes the state and triggers recomposition.

## 4. Key Screens

### Home & Navigation (Portrait)
*   **Bottom Navigation:** Home, Workouts, Stats, More. (Camera is *not* a tab).
*   **Hero Action:** Massive prominent card/FAB to "Start Workout".
*   **Dashboard:** High-level summary (Weekly FG%, Total Shots) using MD3 elevated cards.

### Live Workout Screen (Landscape)
*   **Immersive Mode:** System bars hidden. CameraX preview fills 100% of the screen.
*   **Floating HUD:** No solid background panels. Text has subtle dark drop-shadows.
*   **Edge Alignment:** Metrics pushed to the bottom left (Makes/Misses) and bottom right (Massive FG%) to keep the hoop clear in the center.
*   **Transient Feedback:** Made/Missed shots trigger a 1.5-second massive text overlay in the center of the screen, scaling in and fading out automatically.
*   **System Status:** Minimal top-edge badge indicating tracking health (`TRACKING`, `FINDING RIM`, `MOVE CAMERA`).

### Post-Workout Results & Statistics
*   **Transition:** FG% animates from 0 to final score.
*   **Hierarchy:** Hero stat (percentage), secondary stats (makes/misses split), session metadata (duration).
*   **MD3 Components:** Use filter chips for data segmentation (e.g., filtering charts by day/week/month).

## 5. Integration with Current CV Engine (YOLO11s TFLite)
The newly trained `model.tflite` (exported from the Colab pipeline) serves as the brain of the app. The transition requires a bridge between the Android hardware (Camera), the AI model, and the Compose UI.

### The Connection Pipeline (The "Bridge")
*   **CameraX `ImageAnalysis` Use Case:** Captures raw frames from the device camera and converts them into Bitmaps/ByteBuffers compatible with TFLite.
*   **`ml/YoloDetector.kt`:** The interpreter wrapper. It loads the `model.tflite` file from the `assets` folder, scales the 1080p camera frames down to `640x640` (the size the model was trained on), runs inference, and outputs standard bounding box coordinates (e.g., `[class: basketball, x, y, w, h]`).
*   **`cv/ShotTrackerLogic.kt`:** The state machine. It does not touch the UI. It tracks the bounding boxes across multiple frames (e.g., tracking the basketball bounding box passing through the rim bounding box from above) and emits events like `OnMakeDetected` or `OnMissDetected`.

### Connecting the Bridge to the UI
*   **`workout/WorkoutViewModel.kt`:** The central nervous system. It listens to `ShotTrackerLogic.kt`. When an `OnMakeDetected` event fires, the ViewModel increments the score (`makes++`, recalculates `percentage`) and updates the `WorkoutUiState`.
*   **`workout/BoundingBoxOverlay.kt`:** A Jetpack Compose `<Canvas>` component that sits directly on top of the CameraX preview. It listens to the live bounding box coordinates from `YoloDetector.kt`, scales the `640x640` coordinates back up to the screen's actual dimensions, and draws thin, non-intrusive rectangles around the ball and rim.

## 6. Component Structure
Organize Android Kotlin files by feature and domain:
```text
app/src/main/
├── assets/         (model.tflite, labels.txt)
├── cv/             (ShotTrackerLogic.kt)
├── ml/             (YoloDetector.kt, BoundingBox.kt)
├── ui/
│   ├── theme/      (Color.kt, Theme.kt, Type.kt)
│   ├── components/ (StatCard.kt, BoundingBoxOverlay.kt, TransientOverlay.kt)
│   ├── home/       (HomeScreen.kt, HomeViewModel.kt)
│   ├── workout/    (WorkoutScreen.kt, WorkoutViewModel.kt, CameraPreviewLayer.kt)
│   └── statistics/ (StatisticsScreen.kt)