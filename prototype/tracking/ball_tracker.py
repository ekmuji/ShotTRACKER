"""
Ball Tracker
============
Wraps BallDetector with a lightweight Kalman filter (implemented in pure
NumPy — no filterpy dependency) to smooth positions and predict the ball's
position when detection fails for a few frames.

Tracked state vector: [x, y, vx, vy]
    x, y   – centre position  (pixels)
    vx, vy – velocity         (pixels / frame)

Also records the full trajectory (position history) for downstream
shot-arc analysis.
"""

from __future__ import annotations

import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Deque

from core.ball_detector import BallDetection, BallDetector


# ---------------------------------------------------------------------------
# Minimal Kalman filter (constant-velocity model)
# ---------------------------------------------------------------------------

class _KalmanCV:
    """Constant-velocity Kalman filter for 2-D position tracking."""

    def __init__(self, dt: float = 1.0, process_noise: float = 5.0,
                 measurement_noise: float = 10.0):
        # State: [x, y, vx, vy]
        self.x  = np.zeros((4, 1), dtype=float)          # state
        self.P  = np.eye(4) * 500.0                       # state covariance
        self.dt = dt

        # Transition matrix (constant velocity)
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0,  dt],
            [0, 0, 1,  0],
            [0, 0, 0,  1],
        ], dtype=float)

        # Measurement matrix (we observe x, y only)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)

        # Process noise covariance
        q = process_noise
        self.Q = np.diag([q, q, q * 2, q * 2])

        # Measurement noise covariance
        r = measurement_noise
        self.R = np.diag([r, r])

        self.initialised = False

    # ------------------------------------------------------------------

    def initialise(self, x: float, y: float) -> None:
        self.x = np.array([[x], [y], [0.0], [0.0]], dtype=float)
        self.P = np.eye(4) * 500.0
        self.initialised = True

    def predict(self) -> tuple[float, float]:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return float(self.x[0, 0]), float(self.x[1, 0])

    def update(self, x_meas: float, y_meas: float) -> tuple[float, float]:
        z = np.array([[x_meas], [y_meas]], dtype=float)
        y = z - self.H @ self.x                           # innovation
        S = self.H @ self.P @ self.H.T + self.R          # innovation cov
        K = self.P @ self.H.T @ np.linalg.inv(S)         # Kalman gain
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def position(self) -> tuple[float, float]:
        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def velocity(self) -> tuple[float, float]:
        return float(self.x[2, 0]), float(self.x[3, 0])


# ---------------------------------------------------------------------------
# Trajectory point
# ---------------------------------------------------------------------------

@dataclass
class TrajectoryPoint:
    frame_idx: int
    x: float
    y: float
    vx: float
    vy: float
    detected: bool   # True = real detection; False = Kalman prediction


# ---------------------------------------------------------------------------
# Ball Tracker
# ---------------------------------------------------------------------------

class BallTracker:
    """
    Stateful tracker: feed frames one by one, get smoothed positions back.

    Parameters
    ----------
    max_missing_frames : int
        After this many consecutive missed detections the tracker resets.
    history_len : int
        Maximum trajectory points kept in memory.
    """

    def __init__(
        self,
        detector: Optional[BallDetector] = None,
        max_missing_frames: int = 8,
        history_len: int = 120,
        process_noise: float = 8.0,
        measurement_noise: float = 12.0,
    ):
        self.detector = detector or BallDetector()
        self.max_missing = max_missing_frames
        self._kf = _KalmanCV(process_noise=process_noise,
                              measurement_noise=measurement_noise)
        self._missing_streak: int = 0
        self._frame_idx: int = 0
        self.trajectory: Deque[TrajectoryPoint] = deque(maxlen=history_len)
        self.last_detection: Optional[BallDetection] = None
        self.is_tracking: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, frame: np.ndarray) -> Optional[TrajectoryPoint]:
        """
        Process one frame.  Returns the current best estimate of the ball's
        position as a TrajectoryPoint, or None if the ball is lost.
        """
        raw = self.detector.detect(frame)
        pt  = self._step(raw)
        self._frame_idx += 1
        return pt

    def reset(self) -> None:
        """Reset tracker state (call between workout sessions)."""
        self._kf = _KalmanCV()
        self._missing_streak = 0
        self._frame_idx = 0
        self.trajectory.clear()
        self.last_detection = None
        self.is_tracking = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _step(self, raw: Optional[BallDetection]) -> Optional[TrajectoryPoint]:
        if raw is not None:
            self.last_detection = raw
            if not self._kf.initialised:
                self._kf.initialise(raw.x, raw.y)
            else:
                self._kf.predict()
                self._kf.update(raw.x, raw.y)
            self._missing_streak = 0
            self.is_tracking = True

        else:
            if not self._kf.initialised or not self.is_tracking:
                return None
            self._missing_streak += 1
            if self._missing_streak > self.max_missing:
                self.is_tracking = False
                return None
            self._kf.predict()  # pure prediction

        px, py   = self._kf.position
        vx, vy   = self._kf.velocity
        detected = raw is not None

        pt = TrajectoryPoint(
            frame_idx=self._frame_idx,
            x=px, y=py, vx=vx, vy=vy,
            detected=detected,
        )
        self.trajectory.append(pt)
        return pt

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def recent_positions(self) -> list[tuple[float, float]]:
        return [(p.x, p.y) for p in self.trajectory]

    @property
    def recent_velocities(self) -> list[tuple[float, float]]:
        return [(p.vx, p.vy) for p in self.trajectory]

    def trajectory_as_array(self) -> np.ndarray:
        """Return Nx4 array [frame, x, y, vy] for arc-fitting."""
        if not self.trajectory:
            return np.empty((0, 4))
        return np.array([[p.frame_idx, p.x, p.y, p.vy]
                          for p in self.trajectory])
