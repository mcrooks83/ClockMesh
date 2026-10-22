"""Core types for clock alignment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClockModelState(str, Enum):
    """Maturity of one clock relationship, independent of fit quality.

    UNOBSERVED has no pairs; ANCHORED has a first correspondence;
    RATE_ESTIMATING has a provisional slope; ALIGNED has an applied learned fit;
    TRACKING evaluates later pairs and fits candidates for explicit acceptance.
    """

    UNOBSERVED = "unobserved"
    ANCHORED = "anchored"
    RATE_ESTIMATING = "rate_estimating"
    ALIGNED = "aligned"
    TRACKING = "tracking"


class ClockModelQuality(str, Enum):
    """Quality labels reserved for consumers or future fit assessment.

    AffineClockModel does not currently assign these labels automatically.
    A model's maturity state alone does not establish its quality.
    """

    UNKNOWN = "unknown"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


@dataclass(frozen=True)
class ClockObservation:
    """Immutable correspondence between source and reference timestamps.

    Attributes:
        source_time: Timestamp in caller-defined, consistent source-clock units.
        reference_time_ns: Corresponding integer reference-clock nanoseconds.

    This record stores a pair as supplied; it performs no timestamp validation,
    unit conversion, unwrapping, or delay correction.
    """

    source_time: int | float
    reference_time_ns: int
