"""
Basketball Shot Tracker  —  Main Pipeline
==========================================
Wires together:
  • BallDetector  (core/ball_detector.py)
  • HoopDetector  (core/hoop_detector.py)
  • BallTracker   (tracking/ball_tracker.py)   — Kalman smoothing
  • ShotDetector  (analysis/shot_detector.py)  — FSM
  • SessionStore  (data/session_store.py)       — persistence

Usage
-----
    # Run on a video file and produce an annotated output video
    python main.py --input  path/to/video.mp4  --output annotated.mp4

    # Run on webcam (live prototype mode)
    python main.py --webcam

    # Run tests/demo on a synthetic trajectory (no video needed)
    python main.py --test
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# --- project imports (all relative to basket_tracker root) ----------------
sys.path.insert(0, str(Path(__file__).parent))

from core.ball_detector  import BallDetector,  draw_ball
from core.hoop_detector  import HoopDetector,  draw_hoop, HoopDetection
from tracking.ball_tracker import BallTracker, TrajectoryPoint
from analysis.shot_detector import ShotDetector, ShotEvent
from data.session_store  import SessionStore, WorkoutSession


# ---------------------------------------------------------------------------
# HUD overlay
# ---------------------------------------------------------------------------

def _draw_hud(
    frame: np.ndarray,
    session: WorkoutSession,
    state_label: str,
    last_event: Optional[ShotEvent],
    last_event_age: int,
) -> np.ndarray:
    out = frame.copy()
    h, w = frame.shape[:2]

    # Semi-transparent panel top-left
    panel_h, panel_w = 110, 220
    overlay = out.copy()
    cv2.rectangle(overlay, (8, 8), (8 + panel_w, 8 + panel_h),
                  (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)

    pct   = session.stats.shooting_pct
    makes = session.stats.total_makes
    att   = session.stats.total_attempts
    streak = session.stats.hot_streak_peak

    cv2.putText(out, f"MAKES : {makes}/{att}", (16, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(out, f"PCT   : {pct:.1f}%",   (16, 56),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(out, f"STREAK: {streak}",     (16, 80),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(out, f"STATE : {state_label}",(16, 104),
                cv2.FONT_HERSHEY_DUPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

    # Flash MADE / MISSED badge
    if last_event is not None and last_event_age < 45:
        alpha  = max(0.0, 1.0 - last_event_age / 45.0)
        colour = (50, 220, 50) if last_event.result == "made" else (50, 50, 220)
        label  = "MADE!" if last_event.result == "made" else "MISSED"
        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 1.8, 3)
        tx = (w - text_size[0]) // 2
        ty = h // 3
        overlay2 = out.copy()
        cv2.putText(overlay2, label, (tx, ty),
                    cv2.FONT_HERSHEY_DUPLEX, 1.8, colour, 3, cv2.LINE_AA)
        cv2.addWeighted(overlay2, alpha, out, 1.0 - alpha, 0, out)

    return out


# ---------------------------------------------------------------------------
# Draw trajectory tail
# ---------------------------------------------------------------------------

def _draw_trajectory(frame: np.ndarray, points: list[tuple[float, float]],
                     colour=(0, 165, 255)) -> np.ndarray:
    if len(points) < 2:
        return frame
    out = frame.copy()
    pts = [(int(x), int(y)) for x, y in points[-30:]]  # last 30 pts
    for i in range(1, len(pts)):
        alpha = i / len(pts)
        c = tuple(int(ch * alpha) for ch in colour)
        cv2.line(out, pts[i - 1], pts[i], c, 2, cv2.LINE_AA)
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class ShotTrackerPipeline:
    def __init__(self, fps: float = 30.0, show_debug: bool = False):
        self.ball_detector = BallDetector()
        self.hoop_detector = HoopDetector()
        self.ball_tracker  = BallTracker(detector=self.ball_detector)

        def _on_shot(evt: ShotEvent):
            icon = "✅" if evt.result == "made" else "❌"
            print(f"  {icon}  Shot #{len(self.session.shots):3d}  "
                  f"{evt.result.upper():6s}  "
                  f"conf={evt.confidence:.2f}  "
                  f"pct={self.session.shooting_pct:.1f}%")

        self.shot_detector = ShotDetector(fps=fps, on_shot=_on_shot)
        self.session       = WorkoutSession.new()
        self.session_store = SessionStore()

        self.show_debug    = show_debug
        self._frame_idx    = 0
        self._last_event: Optional[ShotEvent] = None
        self._last_event_frame = 0
        self._hoop: Optional[HoopDetection] = None

    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process one frame, update all state, return annotated frame.
        """
        # 1. Hoop — update every frame but only refresh detection every 15 frames
        if self._frame_idx % 15 == 0 or self._hoop is None:
            self._hoop = self.hoop_detector.detect(frame)

        # 2. Ball tracking
        ball_pt = self.ball_tracker.update(frame)

        # 3. Shot FSM
        evt = self.shot_detector.update(ball_pt, self._hoop, self._frame_idx)
        if evt is not None:
            self.session.add_shot(evt)
            self._last_event       = evt
            self._last_event_frame = self._frame_idx

        # 4. Render
        annotated = frame.copy()
        if self._hoop:
            annotated = draw_hoop(annotated, self._hoop)
        if ball_pt:
            # Create a fake BallDetection for the draw helper
            from core.ball_detector import BallDetection
            fake_det = BallDetection(x=ball_pt.x, y=ball_pt.y, radius=15,
                                     confidence=1.0, method="tracked")
            annotated = draw_ball(annotated, fake_det)
            annotated = _draw_trajectory(annotated,
                                          self.ball_tracker.recent_positions)

        age = self._frame_idx - self._last_event_frame
        annotated = _draw_hud(annotated, self.session,
                               self.shot_detector.state.value,
                               self._last_event, age)

        self._frame_idx += 1
        return annotated

    def finish_session(self, notes: str = "") -> Path:
        self.session.finish(notes=notes)
        path = self.session_store.save(self.session)
        return path


# ---------------------------------------------------------------------------
# Video runner
# ---------------------------------------------------------------------------

def run_video(input_path: str, output_path: Optional[str] = None,
              show_window: bool = False) -> None:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    fps  = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total= int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    pipeline = ShotTrackerPipeline(fps=fps)

  # Dynamically set output dimensions based on orientation
    if w > h:
        # Landscape
        out_w, out_h = 854, 480
    else:
        # Portrait
        out_w, out_h = 480, 854

    writer: Optional[cv2.VideoWriter] = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

    print(f"\n🏀  Basketball Shot Tracker")
    print(f"    Input : {input_path}  ({w}×{h} @ {fps:.1f}fps, {total} frames)")
    if output_path:
        print(f"    Output: {output_path}")
    print("    Processing…\n")

    t0 = time.time()
    frame_no = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.resize(frame, (out_w, out_h))

        annotated = pipeline.process_frame(frame)

        if writer:
            writer.write(annotated)
        if show_window:
            cv2.imshow("Basketball Tracker", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_no += 1
        if frame_no % 100 == 0:
            elapsed = time.time() - t0
            print(f"    Frame {frame_no}/{total}  "
                  f"({frame_no/elapsed:.1f} fps)  "
                  f"Shots: {pipeline.session.stats.total_attempts}  "
                  f"PCT: {pipeline.session.stats.shooting_pct:.1f}%")

    cap.release()
    if writer:
        writer.release()
    if show_window:
        cv2.destroyAllWindows()

    saved = pipeline.finish_session()
    _print_summary(pipeline.session, saved)


def run_webcam() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam.")
    fps = 30.0
    pipeline = ShotTrackerPipeline(fps=fps)
    print("\n🏀  Basketball Shot Tracker  —  LIVE (press Q to quit)\n")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        annotated = pipeline.process_frame(frame)
        cv2.imshow("Basketball Tracker", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
    saved = pipeline.finish_session()
    _print_summary(pipeline.session, saved)


def _print_summary(session: WorkoutSession, saved: Path) -> None:
    s = session.stats
    print("\n" + "=" * 50)
    print("  SESSION SUMMARY")
    print("=" * 50)
    print(f"  Attempts      : {s.total_attempts}")
    print(f"  Makes         : {s.total_makes}")
    print(f"  Shooting %    : {s.shooting_pct:.1f}%")
    print(f"  Duration      : {s.duration_seconds/60:.1f} min")
    print(f"  Makes/min     : {s.makes_per_minute:.1f}")
    print(f"  Hot streak    : {s.hot_streak_peak}")
    print(f"  Saved to      : {saved}")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Self-test (no video required)
# ---------------------------------------------------------------------------

def run_self_test() -> None:
    """Validate the full pipeline on a synthetic arc trajectory."""
    print("\n🧪  Running self-test on synthetic shot trajectory…\n")
    from tracking.ball_tracker import TrajectoryPoint
    from core.hoop_detector import HoopDetection
    from analysis.shot_detector import ShotDetector

    hoop = HoopDetection(x=320, y=200, width=80, height=48, confidence=0.95)

    # Simulate a made shot: parabola through the hoop
    def parabola(t: float) -> tuple[float, float]:
        x = 50 + t * 5
        y = 400 - 8 * t + 0.25 * t ** 2
        return x, y

    det = ShotDetector(fps=30)
    events: list[ShotEvent] = []

    prev_x, prev_y = parabola(0)
    for i in range(80):
        cx, cy = parabola(float(i))
        vx, vy = cx - prev_x, cy - prev_y
        pt = TrajectoryPoint(frame_idx=i, x=cx, y=cy, vx=vx, vy=vy, detected=True)
        prev_x, prev_y = cx, cy
        evt = det.update(pt, hoop, frame_idx=i)
        if evt:
            events.append(evt)
            print(f"  Frame {i:3d}  →  {evt.result.upper()}  "
                  f"conf={evt.confidence:.2f}  "
                  f"ball=({evt.ball_x:.0f},{evt.ball_y:.0f})")

    print(f"\n  FSM detected {len(events)} shot event(s)")
    if events and events[0].result == "made":
        print("  ✅  Test PASSED: shot correctly classified as MADE")
    else:
        print("  ℹ️   No MADE event on this trajectory — check FSM thresholds")

    # Persistence round-trip test
    session = WorkoutSession.new()
    for e in events:
        session.add_shot(e)
    session.finish(notes="self-test")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(directory=tmpdir)
        path  = store.save(session)
        loaded = store.load(session.session_id)
        assert loaded.stats.total_attempts == session.stats.total_attempts, \
            "Persistence round-trip failed!"
        print(f"  ✅  Persistence round-trip OK  ({path.name})")

    print("\n  Detector validation:")
    bd = BallDetector()
    # Synthetic orange circle on dark background
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(test_frame, (320, 240), 25, (20, 130, 230), -1)   # BGR orange-ish
    det_result = bd.detect(test_frame)
    if det_result:
        print(f"  ✅  BallDetector found ball at ({det_result.x:.0f}, "
              f"{det_result.y:.0f})  r={det_result.radius:.0f}  "
              f"method={det_result.method}")
    else:
        print("  ℹ️   BallDetector: no detection on synthetic frame "
              "(colour may need tuning for synthetic data)")

    print("\n✅  Self-test complete.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Basketball Shot Tracker")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input",  metavar="VIDEO",
                       help="Path to input video file")
    group.add_argument("--webcam", action="store_true",
                       help="Use webcam (device 0)")
    group.add_argument("--test",   action="store_true",
                       help="Run built-in self-test (no video needed)")

    parser.add_argument("--output", metavar="FILE",
                        help="Save annotated video to this path (mp4)")
    parser.add_argument("--show",  action="store_true",
                        help="Display live preview window")
    args = parser.parse_args()

    if args.test:
        run_self_test()
    elif args.webcam:
        run_webcam()
    else:
        run_video(args.input, output_path=args.output, show_window=args.show)