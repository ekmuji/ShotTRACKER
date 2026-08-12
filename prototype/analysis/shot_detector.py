"""
Shot Detector  (State Machine)
==============================
Consumes the smoothed ball trajectory and hoop position frame-by-frame.
Uses a finite state machine (FSM) to classify shot attempts and outcomes.

         ┌──────────┐
         │  IDLE    │  Ball not in motion / not detected
         └────┬─────┘
              │  Ball rises significantly (vy < −RISE_THRESH)
              ▼
         ┌──────────┐
         │ RISING   │  Ball moving upward — shot may be in flight
         └────┬─────┘
              │  Ball begins to descend AND is above hoop
              ▼
         ┌──────────┐
         │ PEAK     │  Apex detected — commit this as a shot attempt
         └────┬─────┘
              │  Ball descending toward hoop zone
              ▼
         ┌──────────┐
         │DESCENDING│  Tracking ball on the way down
         └────┬─────┘
              │  Ball crosses hoop plane (y ≈ hoop.y)
              ▼
         ┌──────────┐
         │EVALUATING│  Did the ball pass through the rim?
         └────┬─────┘
              │  MADE: ball centre passed inside rim AND moved below it
              │  MISSED: ball deviated outside rim / disappeared elsewhere
              ▼
         ┌──────────┐
         │COOLDOWN  │  Short refractory period to avoid double-counting
         └──────────┘
              │  After N frames → back to IDLE
              ▼

Output events: ShotEvent(result="made"|"missed", ...)
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
import numpy as np

from tracking.ball_tracker import TrajectoryPoint
from core.hoop_detector import HoopDetection


# ---------------------------------------------------------------------------
# Output event
# ---------------------------------------------------------------------------

@dataclass
class ShotEvent:
    result: str            # "made" or "missed"
    timestamp: float       # time.time() at event
    frame_idx: int
    ball_x: float          # ball position at evaluation moment
    ball_y: float
    hoop_x: float
    hoop_y: float
    confidence: float      # 0–1


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------

class ShotState(enum.Enum):
    IDLE       = "idle"
    RISING     = "rising"
    PEAK       = "peak"
    DESCENDING = "descending"
    EVALUATING = "evaluating"
    COOLDOWN   = "cooldown"


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class ShotDetector:
    """
    Frame-by-frame shot FSM.

    Parameters
    ----------
    rise_thresh       : Upward velocity (pixels/frame) needed to enter RISING.
    descent_thresh    : Downward velocity to confirm peak has passed.
    hoop_y_tolerance  : ±pixels around hoop.y that count as "at hoop height".
    made_x_tolerance  : Ball must be within this many pixels of hoop centre x.
    made_y_tolerance  : Ball must pass this many pixels below hoop.y.
    min_rise_frames   : Minimum frames in RISING before a peak is valid.
    cooldown_frames   : Frames to wait after a shot before resetting to IDLE.
    on_shot           : Optional callback(ShotEvent) for real-time notification.
    """

    def __init__(
        self,
        fps: float = 30.0,
        rise_thresh: float = 3.0,
        descent_thresh: float = 2.0,
        hoop_y_tolerance: float = 40.0,
        made_x_tolerance_factor: float = 0.55,  # fraction of hoop half-width
        made_y_below: float = 20.0,
        min_rise_frames: int = 4,
        cooldown_frames: int = 20,
        on_shot: Optional[Callable[[ShotEvent], None]] = None,
    ):
        self.fps = fps
        self.rise_thresh   = rise_thresh
        self.descent_thresh = descent_thresh
        self.hoop_y_tol    = hoop_y_tolerance
        self.made_x_factor = made_x_tolerance_factor
        self.made_y_below  = made_y_below
        self.min_rise      = min_rise_frames
        self.cooldown_max  = cooldown_frames
        self.on_shot       = on_shot

        self._state        = ShotState.IDLE
        self._rise_frames  = 0
        self._cooldown_ctr = 0
        self._peak_pt: Optional[TrajectoryPoint] = None

        # Shot log
        self.shots: list[ShotEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        ball_pt: Optional[TrajectoryPoint],
        hoop: Optional[HoopDetection],
        frame_idx: int,
    ) -> Optional[ShotEvent]:
        """
        Feed the latest tracker point and hoop position.
        Returns a ShotEvent if a shot outcome is determined, else None.
        """
        if self._state == ShotState.COOLDOWN:
            self._cooldown_ctr += 1
            if self._cooldown_ctr >= self.cooldown_max:
                self._reset()
            return None

        if ball_pt is None or hoop is None:
            # If we lose the ball mid-shot and we were descending, call it a miss
            if self._state in (ShotState.DESCENDING, ShotState.EVALUATING):
                return self._emit("missed", ball_pt, hoop, frame_idx,
                                   confidence=0.3)
            return None

        vx, vy = ball_pt.vx, ball_pt.vy  # vy < 0 = moving up (screen coords)
        bx, by  = ball_pt.x, ball_pt.y

        # ---- State transitions ----------------------------------------
        if self._state == ShotState.IDLE:
            if vy < -self.rise_thresh:   # ball moving up
                self._state = ShotState.RISING
                self._rise_frames = 1

        elif self._state == ShotState.RISING:
            if vy < -self.rise_thresh:
                self._rise_frames += 1
            elif vy >= -self.descent_thresh:
                # Velocity switched to descent/flat — peak reached
                if self._rise_frames >= self.min_rise:
                    self._peak_pt = ball_pt
                    self._state = ShotState.PEAK
                else:
                    self._reset()   # too brief — noise
            # (stay in RISING while still ascending)

        elif self._state == ShotState.PEAK:
            # Wait for the ball to start descending
            if vy > self.descent_thresh:
                self._state = ShotState.DESCENDING

        elif self._state == ShotState.DESCENDING:
            # Check if ball is in the hoop evaluation zone
            if abs(by - hoop.y) < self.hoop_y_tol:
                self._state = ShotState.EVALUATING
            # If ball has gone far below hoop, it's a clear miss
            if by > hoop.y + hoop.height * 2:
                return self._emit("missed", ball_pt, hoop, frame_idx,
                                   confidence=0.75)

        elif self._state == ShotState.EVALUATING:
            result = self._evaluate(ball_pt, hoop)
            if result is not None:
                return self._emit(result, ball_pt, hoop, frame_idx,
                                   confidence=0.85 if result == "made" else 0.70)

        return None

    # ------------------------------------------------------------------

    def reset_session(self) -> None:
        """Clear shot history and FSM state."""
        self._reset()
        self.shots.clear()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> ShotState:
        return self._state

    @property
    def makes(self) -> int:
        return sum(1 for s in self.shots if s.result == "made")

    @property
    def attempts(self) -> int:
        return len(self.shots)

    @property
    def shooting_pct(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.makes / self.attempts * 100.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate(
        self,
        pt: TrajectoryPoint,
        hoop: HoopDetection,
    ) -> Optional[str]:
        """
        During EVALUATING: decide "made", "missed", or None (keep watching).
        """
        bx, by = pt.x, pt.y
        hx, hy = hoop.x, hoop.y
        allowed_dx = hoop.width / 2 * self.made_x_factor

        # Ball passed through the plane of the rim
        if by > hy + self.made_y_below:
            dx = abs(bx - hx)
            if dx < allowed_dx:
                return "made"
            else:
                return "missed"

        # Ball went far off to the side
        if abs(bx - hx) > hoop.width * 1.8:
            return "missed"

        return None   # still watching

    def _emit(
        self,
        result: str,
        ball_pt: Optional[TrajectoryPoint],
        hoop: Optional[HoopDetection],
        frame_idx: int,
        confidence: float,
    ) -> ShotEvent:
        evt = ShotEvent(
            result=result,
            timestamp=time.time(),
            frame_idx=frame_idx,
            ball_x=ball_pt.x if ball_pt else 0.0,
            ball_y=ball_pt.y if ball_pt else 0.0,
            hoop_x=hoop.x  if hoop else 0.0,
            hoop_y=hoop.y  if hoop else 0.0,
            confidence=confidence,
        )
        self.shots.append(evt)
        self._enter_cooldown()
        if self.on_shot:
            self.on_shot(evt)
        return evt

    def _reset(self) -> None:
        self._state = ShotState.IDLE
        self._rise_frames = 0
        self._peak_pt = None

    def _enter_cooldown(self) -> None:
        self._state = ShotState.COOLDOWN
        self._cooldown_ctr = 0
        self._peak_pt = None
        self._rise_frames = 0
