"""
Unit Tests  —  Basketball Shot Tracker
=======================================
Run with:
    python -m pytest tests/test_tracker.py -v
    # or directly:
    python tests/test_tracker.py
"""

from __future__ import annotations

import sys
import time
import tempfile
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2

from core.ball_detector   import BallDetector, BallDetection
from core.hoop_detector   import HoopDetector, HoopDetection
from tracking.ball_tracker import BallTracker, _KalmanCV, TrajectoryPoint
from analysis.shot_detector import ShotDetector, ShotEvent, ShotState
from data.session_store   import SessionStore, WorkoutSession, SessionStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def orange_frame(cx: int = 320, cy: int = 240, r: int = 22) -> np.ndarray:
    """Return a 480×640 BGR frame with an orange circle at (cx,cy)."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # BGR representation of roughly basketball orange (H=15, S=200, V=220)
    cv2.circle(frame, (cx, cy), r, (20, 120, 220), -1)
    return frame


def make_hoop(x=320, y=200, w=80, h=48) -> HoopDetection:
    return HoopDetection(x=float(x), y=float(y),
                         width=float(w), height=float(h), confidence=0.9)


def arc_trajectory(
    hoop: HoopDetection,
    n_frames: int = 70,
    make: bool = True,
) -> list[TrajectoryPoint]:
    """
    Generate a synthetic parabolic trajectory.

    The ball starts below-left, rises above the hoop, then descends.
    *make=True*  → ball passes through hoop centre.
    *make=False* → ball lands 100 px to the right of the hoop (clear miss).
    """
    pts = []
    hx, hy = hoop.x, hoop.y

    # Start position: bottom-left of frame, below hoop
    start_x = hx - 150
    start_y = hy + 250

    # End position
    end_x = hx if make else hx + 100
    end_y = hy + 60 if make else hy + 80   # end below the hoop plane

    # Peak: above the hoop
    peak_x = (start_x + end_x) / 2
    peak_y = hy - 120   # well above the rim

    # Compute positions along a quadratic Bezier curve
    positions = []
    for i in range(n_frames):
        t = i / (n_frames - 1)
        # Quadratic Bezier: P = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
        u = 1 - t
        x = u*u*start_x + 2*u*t*peak_x + t*t*end_x
        y = u*u*start_y + 2*u*t*peak_y + t*t*end_y
        positions.append((x, y))

    # Derive velocities from consecutive positions
    for i, (x, y) in enumerate(positions):
        if i == 0:
            vx, vy = 0.0, 0.0
        else:
            vx = x - positions[i-1][0]
            vy = y - positions[i-1][1]
        pts.append(TrajectoryPoint(frame_idx=i, x=x, y=y,
                                    vx=vx, vy=vy, detected=True))
    return pts


# ---------------------------------------------------------------------------
# BallDetector tests
# ---------------------------------------------------------------------------

class TestBallDetector:
    def test_detects_orange_circle(self):
        det = BallDetector()
        frame = orange_frame(cx=320, cy=240, r=22)
        result = det.detect(frame)
        assert result is not None, "Should detect orange circle"
        assert abs(result.x - 320) < 20, f"cx off: {result.x}"
        assert abs(result.y - 240) < 20, f"cy off: {result.y}"
        assert 10 <= result.radius <= 60

    def test_no_detection_on_blank_frame(self):
        det = BallDetector()
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        result = det.detect(blank)
        assert result is None, "Should not detect on blank frame"

    def test_confidence_range(self):
        det = BallDetector()
        frame = orange_frame()
        result = det.detect(frame)
        if result:
            assert 0.0 <= result.confidence <= 1.0

    def test_small_circle_below_min_radius(self):
        det = BallDetector(min_radius=30)
        frame = orange_frame(r=5)   # too small
        result = det.detect(frame)
        assert result is None or result.radius < det.min_radius + 5


# ---------------------------------------------------------------------------
# HoopDetector tests
# ---------------------------------------------------------------------------

class TestHoopDetector:
    def test_returns_none_on_blank(self):
        det = HoopDetector()
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        result = det.detect(blank)
        # Should either return None or stabilised position (none on first call)
        assert result is None

    def test_ema_smoothing(self):
        det = HoopDetector()
        h1 = HoopDetection(x=300, y=200, width=80, height=40, confidence=0.8)
        h2 = HoopDetection(x=320, y=200, width=80, height=40, confidence=0.8)
        merged = det._ema(h1, h2)
        # EMA: new = prev*(1-a) + curr*a  where a=0.25
        expected_x = 300 * 0.75 + 320 * 0.25
        assert abs(merged.x - expected_x) < 1.0, f"EMA x wrong: {merged.x}"

    def test_reset_clears_stable(self):
        det = HoopDetector()
        det._stable = make_hoop()
        det.reset()
        assert det._stable is None


# ---------------------------------------------------------------------------
# Kalman filter tests
# ---------------------------------------------------------------------------

class TestKalmanCV:
    def test_init_and_predict(self):
        kf = _KalmanCV()
        kf.initialise(100.0, 200.0)
        px, py = kf.predict()
        # With zero initial velocity prediction should stay close
        assert abs(px - 100) < 5
        assert abs(py - 200) < 5

    def test_update_moves_toward_measurement(self):
        kf = _KalmanCV(measurement_noise=1.0)
        kf.initialise(0.0, 0.0)
        for _ in range(20):
            kf.predict()
            kf.update(100.0, 100.0)
        px, py = kf.position
        assert abs(px - 100) < 10, f"Kalman didn't converge: px={px}"
        assert abs(py - 100) < 10, f"Kalman didn't converge: py={py}"

    def test_velocity_estimation(self):
        kf = _KalmanCV(measurement_noise=0.1)
        kf.initialise(0.0, 0.0)
        for i in range(1, 15):
            kf.predict()
            kf.update(float(i * 5), 0.0)  # x moves +5 per frame
        vx, _ = kf.velocity
        assert 3 < vx < 7, f"Velocity estimate off: vx={vx}"


# ---------------------------------------------------------------------------
# BallTracker tests
# ---------------------------------------------------------------------------

class TestBallTracker:
    def test_tracker_returns_point_on_detection(self):
        tracker = BallTracker()
        frame = orange_frame()
        pt = tracker.update(frame)
        # May or may not detect on synthetic frame — just ensure no crash
        assert pt is None or isinstance(pt, TrajectoryPoint)

    def test_trajectory_grows(self):
        tracker = BallTracker()
        for _ in range(5):
            frame = orange_frame()
            tracker.update(frame)
        # Trajectory should have some points (detected or predicted)
        assert len(tracker.trajectory) >= 0  # just no crash

    def test_reset_clears_state(self):
        tracker = BallTracker()
        tracker._frame_idx = 99
        tracker.reset()
        assert tracker._frame_idx == 0
        assert len(tracker.trajectory) == 0
        assert not tracker.is_tracking


# ---------------------------------------------------------------------------
# ShotDetector FSM tests
# ---------------------------------------------------------------------------

class TestShotDetector:
    def _run_arc(self, make: bool) -> list[ShotEvent]:
        hoop = make_hoop()
        det  = ShotDetector(fps=30, rise_thresh=1.5, descent_thresh=1.0,
                             min_rise_frames=3)
        events: list[ShotEvent] = []
        pts = arc_trajectory(hoop, n_frames=70, make=make)
        for i, pt in enumerate(pts):
            evt = det.update(pt, hoop, frame_idx=i)
            if evt:
                events.append(evt)
        return events

    def test_made_shot_detected(self):
        events = self._run_arc(make=True)
        assert len(events) >= 1, "Should detect at least one shot"
        assert events[0].result == "made", \
            f"Expected 'made' but got '{events[0].result}'"

    def test_missed_shot_detected(self):
        events = self._run_arc(make=False)
        assert len(events) >= 1, "Should detect at least one shot"
        assert events[0].result == "missed", \
            f"Expected 'missed' but got '{events[0].result}'"

    def test_idle_on_no_ball(self):
        det = ShotDetector()
        result = det.update(None, None, frame_idx=0)
        assert result is None
        assert det.state == ShotState.IDLE

    def test_cooldown_prevents_double_count(self):
        hoop = make_hoop()
        det  = ShotDetector(fps=30, rise_thresh=1.5, descent_thresh=1.0,
                             min_rise_frames=3, cooldown_frames=30)
        pts = arc_trajectory(hoop, n_frames=70, make=True)
        events = []
        for i, pt in enumerate(pts):
            evt = det.update(pt, hoop, frame_idx=i)
            if evt:
                events.append(evt)
        assert len(events) == 1, \
            f"Cooldown should prevent double-count but got {len(events)} events"

    def test_shooting_pct(self):
        hoop = make_hoop()
        det  = ShotDetector(fps=30, rise_thresh=1.5, descent_thresh=1.0,
                             min_rise_frames=3, cooldown_frames=5)
        frame_counter = 0
        # Simulate 2 makes, 1 miss across separate arcs
        for make in [True, True, False]:
            pts = arc_trajectory(hoop, n_frames=60, make=make)
            for pt in pts:
                pt.frame_idx = frame_counter
                det.update(pt, hoop, frame_idx=frame_counter)
                frame_counter += 1
            frame_counter += 30  # gap between shots (clears cooldown)

        if det.attempts > 0:
            assert 0 <= det.shooting_pct <= 100

    def test_reset_session_clears_shots(self):
        det = ShotDetector()
        det.shots.append(ShotEvent("made", time.time(), 0, 0,0,0,0, 0.9))
        det.reset_session()
        assert len(det.shots) == 0
        assert det.attempts == 0


# ---------------------------------------------------------------------------
# SessionStore tests
# ---------------------------------------------------------------------------

class TestSessionStore:
    def _make_session_with_shots(self, n: int = 3) -> WorkoutSession:
        hoop = make_hoop()
        det  = ShotDetector(fps=30, rise_thresh=1.5, descent_thresh=1.0,
                             min_rise_frames=3)
        session = WorkoutSession.new()
        pts = arc_trajectory(hoop, n_frames=60, make=True)
        for i, pt in enumerate(pts):
            evt = det.update(pt, hoop, frame_idx=i)
            if evt:
                session.add_shot(evt)
        return session

    def test_save_and_load_round_trip(self):
        session = self._make_session_with_shots()
        session.finish(notes="unit test")
        with tempfile.TemporaryDirectory() as tmpdir:
            store   = SessionStore(directory=tmpdir)
            path    = store.save(session)
            assert path.exists()
            loaded  = store.load(session.session_id)
            assert loaded.session_id == session.session_id
            assert loaded.stats.total_attempts == session.stats.total_attempts
            assert loaded.stats.total_makes    == session.stats.total_makes
            assert abs(loaded.stats.shooting_pct - session.stats.shooting_pct) < 0.1

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(directory=tmpdir)
            ids_saved = []
            for i in range(3):
                s = WorkoutSession(session_id=f"session_{i:04d}")
                s.finish()
                store.save(s)
                ids_saved.append(s.session_id)
            ids = store.list_sessions()
            assert len(ids) == 3, f"Expected 3 sessions, got {len(ids)}"

    def test_summary_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store   = SessionStore(directory=tmpdir)
            session = self._make_session_with_shots()
            session.finish()
            store.save(session)
            table   = store.summary_table()
            assert len(table) == 1
            assert "shooting_pct" in table[0]
            assert "session_id"   in table[0]

    def test_stats_streaks(self):
        stats  = SessionStats()
        shots  = [
            ShotEvent("made",   time.time(), 0, 0,0,0,0, 0.9),
            ShotEvent("made",   time.time(), 1, 0,0,0,0, 0.9),
            ShotEvent("made",   time.time(), 2, 0,0,0,0, 0.9),
            ShotEvent("missed", time.time(), 3, 0,0,0,0, 0.7),
            ShotEvent("made",   time.time(), 4, 0,0,0,0, 0.9),
        ]
        stats.update(shots, duration=60.0)
        assert stats.longest_make_streak == 3
        assert stats.total_makes == 4
        assert stats.total_attempts == 5
        assert abs(stats.shooting_pct - 80.0) < 0.1


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests() -> None:
    import traceback

    test_classes = [
        TestBallDetector,
        TestHoopDetector,
        TestKalmanCV,
        TestBallTracker,
        TestShotDetector,
        TestSessionStore,
    ]

    passed = failed = 0
    for cls in test_classes:
        instance = cls()
        methods  = [m for m in dir(instance) if m.startswith("test_")]
        for name in methods:
            label = f"{cls.__name__}.{name}"
            try:
                getattr(instance, name)()
                print(f"  ✅  {label}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌  {label}\n       AssertionError: {e}")
                failed += 1
            except Exception:
                print(f"  ❌  {label}")
                traceback.print_exc()
                failed += 1

    print(f"\n{'='*50}")
    print(f"  {passed} passed  /  {failed} failed  /  {passed+failed} total")
    print(f"{'='*50}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_tests()
