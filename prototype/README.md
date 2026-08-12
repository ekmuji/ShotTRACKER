# 🏀 Basketball Shot Tracker — Python Prototype

A proof-of-concept computer-vision pipeline that automatically detects
basketball shots (makes and misses) from a video feed.

## Architecture

```
basketball_tracker/
├── core/
│   ├── ball_detector.py    — Orange-ball detection (HSV + Hough circles)
│   └── hoop_detector.py    — Rim detection (edge + ellipse fitting + EMA)
├── tracking/
│   └── ball_tracker.py     — Kalman-filter smoothing + trajectory history
├── analysis/
│   └── shot_detector.py    — FSM: IDLE → RISING → PEAK → DESCENDING → EVALUATE
├── data/
│   └── session_store.py    — Workout sessions, stats, JSON persistence
├── tests/
│   └── test_tracker.py     — 23 unit tests (all pass)
├── main.py                 — End-to-end pipeline + CLI
└── requirements.txt
```

## Detection Pipeline

```
Frame
 │
 ├─► BallDetector  ──────────────────────────────────────────►┐
 │    HSV colour seg + Hough circles → merged BallDetection   │
 │                                                             │
 ├─► HoopDetector (every 15 frames) ────────────────────────►┤
 │    Edge → Hough circles + ellipse fit → EMA stabilise      │
 │                                                             │
 ▼                                                             ▼
BallTracker (Kalman filter)          ShotDetector (FSM)
 Smoothed (x,y,vx,vy)               IDLE → RISING → PEAK
 + trajectory deque                 → DESCENDING → EVALUATE
                                     → ShotEvent (made/miss)
                                             │
                                             ▼
                                     WorkoutSession + SessionStore
                                     JSON persistence
```

## Shot Detection State Machine

| State      | Entry condition                            | Exit condition                        |
|------------|--------------------------------------------|---------------------------------------|
| IDLE       | Default                                    | vy < −rise_thresh (ball moving up)    |
| RISING     | Ball ascending                             | vy flips positive (apex reached)      |
| PEAK       | Apex detected, shot committed              | vy > descent_thresh                   |
| DESCENDING | Ball falling                               | ball_y ≈ hoop_y (±tolerance)          |
| EVALUATING | Ball in hoop zone                          | Passes inside rim → MADE, else MISSED |
| COOLDOWN   | After any shot outcome (prevents re-count) | After N frames → IDLE                 |

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Run on a video file
python main.py --input footage.mp4 --output annotated.mp4

# Live webcam mode
python main.py --webcam

# Built-in self-test (no video needed)
python main.py --test

# Unit tests
python tests/test_tracker.py
```

## Accuracy Notes

This prototype uses **classical CV** (no ML model):

| Condition                          | Expected Accuracy |
|------------------------------------|-------------------|
| Good lighting, regulation ball     | 70–85%            |
| Mixed lighting, worn ball          | 50–70%            |
| Ball occluded by player            | Lower (tracker predicts 8 frames forward) |

### Known limitations → iOS app mitigations

| Limitation                       | iOS Solution                                  |
|----------------------------------|-----------------------------------------------|
| HSV tuning per environment       | ARKit point cloud for 3-D ball position       |
| Hoop detection unreliable indoors| One-time user tap to anchor hoop position     |
| No perspective compensation      | CoreML YOLOv8 object detector                 |
| 30 fps Python overhead           | Native AVFoundation + Vision framework        |

## iOS Migration Path

1. **Ball detection** → CoreML `YOLOv8n` model (trained on basketball dataset)
2. **Hoop detection** → ARKit plane detection + user confirmation tap
3. **Tracking** → `VNTrackObjectRequest` (Apple's Vision tracker)
4. **Shot FSM** → Direct port of `ShotDetector` to Swift
5. **Persistence** → CoreData or SwiftData replacing JSON store
6. **UI** → SwiftUI overlay on `AVCaptureVideoPreviewLayer`

## Session Data Format

Sessions saved to `~/.basketball_tracker/sessions/<timestamp>.json`:

```json
{
  "session_id": "20240315_143022",
  "start_time": 1710510622.0,
  "end_time":   1710511200.0,
  "stats": {
    "total_attempts": 42,
    "total_makes": 31,
    "shooting_pct": 73.8,
    "duration_seconds": 578.0,
    "makes_per_minute": 3.2,
    "longest_make_streak": 7,
    "hot_streak_peak": 7
  },
  "shots": [ "..." ]
}
```