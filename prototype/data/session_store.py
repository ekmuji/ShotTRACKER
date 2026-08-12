"""
Workout Session  — data model + local JSON persistence
======================================================
Stores all shot events for a session, computes aggregate stats,
and serialises / deserialises to a simple JSON file.

Storage layout (default: ~/.basketball_tracker/sessions/)
    sessions/
        20240315_143022.json
        20240316_090511.json
        ...
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from analysis.shot_detector import ShotEvent


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SessionStats:
    total_attempts: int   = 0
    total_makes: int      = 0
    shooting_pct: float   = 0.0
    duration_seconds: float = 0.0
    makes_per_minute: float = 0.0
    longest_make_streak: int = 0
    longest_miss_streak: int = 0
    hot_streak_peak: int  = 0   # max consecutive makes ever

    def update(self, shots: list[ShotEvent], duration: float) -> None:
        self.total_attempts = len(shots)
        self.total_makes    = sum(1 for s in shots if s.result == "made")
        self.shooting_pct   = (self.total_makes / self.total_attempts * 100
                               if self.total_attempts else 0.0)
        self.duration_seconds = duration
        mins = duration / 60.0
        self.makes_per_minute = self.total_makes / mins if mins > 0 else 0.0

        # Streaks
        cur_make = cur_miss = peak = 0
        best_make = best_miss = 0
        for s in shots:
            if s.result == "made":
                cur_make += 1
                cur_miss  = 0
                if cur_make > peak:
                    peak = cur_make
            else:
                cur_miss += 1
                cur_make  = 0
            best_make = max(best_make, cur_make)
            best_miss = max(best_miss, cur_miss)
        self.longest_make_streak = best_make
        self.longest_miss_streak = best_miss
        self.hot_streak_peak     = peak


@dataclass
class WorkoutSession:
    session_id: str
    start_time: float           = field(default_factory=time.time)
    end_time: Optional[float]   = None
    shots: list[ShotEvent]      = field(default_factory=list)
    stats: SessionStats         = field(default_factory=SessionStats)
    notes: str                  = ""

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @staticmethod
    def new() -> "WorkoutSession":
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return WorkoutSession(session_id=ts)

    def add_shot(self, event: ShotEvent) -> None:
        self.shots.append(event)
        self._refresh_stats()

    def finish(self, notes: str = "") -> None:
        self.end_time = time.time()
        self.notes    = notes
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        dur = (self.end_time or time.time()) - self.start_time
        self.stats.update(self.shots, dur)

    @property
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time

    @property
    def shooting_pct(self) -> float:
        return self.stats.shooting_pct

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "session_id":  self.session_id,
            "start_time":  self.start_time,
            "end_time":    self.end_time,
            "notes":       self.notes,
            "stats":       asdict(self.stats),
            "shots": [
                {
                    "result":     s.result,
                    "timestamp":  s.timestamp,
                    "frame_idx":  s.frame_idx,
                    "ball_x":     s.ball_x,
                    "ball_y":     s.ball_y,
                    "hoop_x":     s.hoop_x,
                    "hoop_y":     s.hoop_y,
                    "confidence": s.confidence,
                }
                for s in self.shots
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkoutSession":
        shots = [
            ShotEvent(
                result=s["result"],
                timestamp=s["timestamp"],
                frame_idx=s["frame_idx"],
                ball_x=s["ball_x"],
                ball_y=s["ball_y"],
                hoop_x=s["hoop_x"],
                hoop_y=s["hoop_y"],
                confidence=s["confidence"],
            )
            for s in d.get("shots", [])
        ]
        stats = SessionStats(**d.get("stats", {}))
        return cls(
            session_id=d["session_id"],
            start_time=d["start_time"],
            end_time=d.get("end_time"),
            shots=shots,
            stats=stats,
            notes=d.get("notes", ""),
        )


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

class SessionStore:
    """Persist and load WorkoutSession objects as JSON files."""

    DEFAULT_DIR = Path.home() / ".basketball_tracker" / "sessions"

    def __init__(self, directory: Optional[Path] = None):
        self.directory = Path(directory) if directory else self.DEFAULT_DIR
        self.directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------

    def save(self, session: WorkoutSession) -> Path:
        path = self.directory / f"{session.session_id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(session.to_dict(), fh, indent=2)
        return path

    def load(self, session_id: str) -> WorkoutSession:
        path = self.directory / f"{session_id}.json"
        with open(path, encoding="utf-8") as fh:
            return WorkoutSession.from_dict(json.load(fh))

    def list_sessions(self) -> list[str]:
        """Return session IDs sorted newest-first."""
        files = sorted(self.directory.glob("*.json"), reverse=True)
        return [f.stem for f in files]

    def load_all(self) -> list[WorkoutSession]:
        sessions = []
        for sid in self.list_sessions():
            try:
                sessions.append(self.load(sid))
            except Exception:
                pass
        return sessions

    def summary_table(self) -> list[dict]:
        """Return a list of dicts suitable for display / export."""
        rows = []
        for session in self.load_all():
            s = session.stats
            rows.append({
                "session_id":    session.session_id,
                "date":          datetime.fromtimestamp(session.start_time).strftime(
                                     "%Y-%m-%d %H:%M"),
                "attempts":      s.total_attempts,
                "makes":         s.total_makes,
                "shooting_pct":  f"{s.shooting_pct:.1f}%",
                "duration_min":  f"{s.duration_seconds / 60:.1f}",
                "hot_streak":    s.hot_streak_peak,
            })
        return rows
