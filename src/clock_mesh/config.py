"""Configuration for clock alignment models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClockAlignmentConfig:
    """Policy controlling clock-model calibration."""

    target_calibration_span_ns: int = 2_000_000_000
    calibration_deadline_ns: int = 5_000_000_000

    min_learned_observations: int = 5

    # Optional known relationship between one source-clock unit
    # and reference nanoseconds.
    #
    # Examples:
    #   milliseconds -> 1_000_000
    #   microseconds -> 1_000
    #   nanoseconds  -> 1
    nominal_scale_ns_per_source_unit: float | None = None
