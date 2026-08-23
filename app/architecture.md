# Basketball Tracker — Architecture

## Project Structure

```
app/src/main/
├── cpp/                         C++ shared core (also used by iOS)
│   ├── CMakeLists.txt           NDK build script
│   ├── TrackerEngine.h          Public plain-C API (cross-platform contract)
│   ├── TrackerEngine.cpp        Kalman filter + EMA hoop + Shot FSM
│   └── TrackerBridge_jni.cpp   Android JNI glue (excluded from iOS build)
│
└── java/com/basketballtracker/
    ├── BasketballTrackerApp.kt  Hilt entry point
    ├── MainActivity.kt          Single-activity host, camera permission
    ├── TrackerBridge.kt         ONLY file that touches JNI — thin wrapper
    ├── BallDetector.kt          TFLite YOLOv8 wrapper (Roboflow model)
    ├── HoopDetector.kt          TFLite YOLOv8 wrapper (Roboflow model)
    ├── CameraService.kt         CameraX — delivers Bitmap frames
    ├── WorkoutViewModel.kt      Connects camera → ML → C++ → UI
    ├── OverlayView.kt           Canvas overlay drawn on PreviewView
    ├── HomeFragment.kt          Landing screen
    ├── WorkoutFragment.kt       Live camera + HUD
    ├── HistoryStatisticsFragments.kt  History + Stats (TODO screens)
    ├── DataLayer.kt             Models, Room entities, DAO, DB, Repository
    └── AppModule.kt             Hilt DI wiring
```

## Data Flow (per frame, ~30 fps)

```
CameraX ImageAnalysis
        │  Bitmap (RGBA_8888)
        ▼
CameraService.FrameCallback
        │
        ▼
WorkoutViewModel.processFrame()
        ├── BallDetector.detect()   → BallDetectionInput  (TFLite, GPU delegate)
        └── HoopDetector.detect()   → HoopDetectionInput  (TFLite, every 15 frames)
                │
                ▼
        TrackerBridge.update()      ← Kotlin→JNI boundary (only crossing point)
                │
                ▼
        tracker_update() in C++
                ├── KalmanFilter2D.predict() + .update()   → smoothed ball pos/vel
                ├── HoopStabiliser.update()                → EMA hoop box
                └── ShotFSM.update()                       → ShotResult
                │
                ▼
        FrameResult (returned by value, no heap allocation)
                │
                ▼
        LiveData.postValue()        → UI thread
                ├── WorkoutFragment  updates HUD TextViews
                └── OverlayView      draws ball + hoop overlay
```

## C++ Engine Internals

| Class | Role |
|---|---|
| `KalmanFilter2D` | Constant-velocity Kalman filter [x, y, vx, vy]; predicts for up to 8 missing frames |
| `HoopStabiliser` | EMA (α=0.20) of the ML hoop box; forgets after 45 missed frames |
| `ShotFSM` | 6-state FSM: IDLE→RISING→PEAK→DESCENDING→EVALUATING→COOLDOWN |

## ML Models (Roboflow)

| Model | Roboflow project | Export | Input | Asset |
|---|---|---|---|---|
| Ball | `basketball-detection` | TFLite FP16 | 320×320 | `ball_detector.tflite` |
| Hoop | `basketball-hoop-detection` | TFLite FP16 | 320×320 | `hoop_detector.tflite` |

Training steps:
1. Collect 500+ images on Roboflow (outdoor court, indoor gym, various lighting).
2. Annotate: ball = one class, hoop = one class.
3. Train YOLOv8-nano (fast enough for 30 fps on mid-range Android).
4. Export → TFLite FP16 → download `.tflite` → place in `app/src/main/assets/`.
5. Verify tensor shapes with [netron.app](https://netron.app) and update `parseOutput()` if needed.

## iOS Reuse Plan

The C++ core (`TrackerEngine.h` + `TrackerEngine.cpp`) compiles unchanged on iOS.
Only `TrackerBridge_jni.cpp` is Android-specific.

```
iOS project:
  ├── TrackerEngine.h          ← copy directly
  ├── TrackerEngine.cpp        ← copy directly
  └── TrackerBridge.swift      ← new Swift wrapper (same API shape as Kotlin bridge)
      └── calls tracker_create / tracker_update / tracker_destroy via bridging header
```

## Key TODOs (in priority order)

1. **Download Roboflow TFLite models** → `assets/ball_detector.tflite` + `assets/hoop_detector.tflite`
2. **Verify tensor shapes** in `BallDetector.parseOutput()` and `HoopDetector.parseOutput()` using netron.app
3. **Wire Hilt into WorkoutFragment** — replace `WorkoutViewModelFactory` with `@HiltViewModel`
4. **Implement StatisticsFragment** — lifetime chart (Vico library recommended)
5. **Implement HistoryFragment** — RecyclerView + SessionAdapter
6. **Bitmap pooling** in `CameraService` — reduces GC pressure at 30 fps
7. **Scale overlay coordinates** in `OverlayView` — use actual bitmap size, not hardcoded 1080×1920
8. **Camera2 manual exposure lock** — prevents flickering during fast ball movement
9. **Add migrations** — replace `fallbackToDestructiveMigration()` in `AppModule`
10. **ProGuard rules** — add TFLite and Room keep rules to `proguard-rules.pro`