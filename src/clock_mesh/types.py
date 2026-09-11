"""Core types for clock alignment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClockModelState(str, Enum):
    """Maturity of a clock relationship."""

    UNOBSERVED = "unobserved"
    ANCHORED = "anchored"
    RATE_ESTIMATING = "rate_estimating"
    ALIGNED = "aligned"
    TRACKING = "tracking"


class ClockModelQuality(str, Enum):
    """Observed quality of a clock fit."""

    UNKNOWN = "unknown"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


@dataclass(frozen=True)
class ClockObservation:
    """One correspondence between a source and reference clock."""

    source_time: int | float
    reference_time_ns: int
