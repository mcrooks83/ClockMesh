"""Configuration for clock alignment models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClockAlignmentConfig:
    """Immutable calibration, candidate-acceptance, and storage settings.

    Attributes:
        target_calibration_span_ns: Minimum retained reference span for automatic
            initial alignment, in nanoseconds.
        calibration_deadline_ns: Deadline metadata for callers; AffineClockModel
            does not enforce elapsed-time watchdogs itself.
        min_learned_observations: Minimum retained pair count for initial alignment
            and candidate acceptance. Storage capacity is not a required count.
        max_calibration_observations: Maximum initial-calibration pairs retained.
        max_tracking_errors: Maximum prediction errors retained for statistics.
        max_tracking_observations: Maximum pairs retained for candidate fitting.
        min_tracking_acceptance_span_ns: Minimum retained reference span before
            accepting a tracking candidate, in nanoseconds.
        nominal_scale_ns_per_source_unit: Optional known nanoseconds per source
            unit, permitting anchored mapping before a learned fit is applied.
        reuse_calibration_history: Seed tracking with retained calibration pairs
            once at initial alignment. Pairs contribute once to the candidate
            fit, with no extra observation counts or tracking errors.
    """

    target_calibration_span_ns: int = 2_000_000_000
    calibration_deadline_ns: int = 5_000_000_000

    min_learned_observations: int = 5

    max_calibration_observations: int = 2_048
    max_tracking_errors: int = 256
    max_tracking_observations: int = 2_048
    min_tracking_acceptance_span_ns: int = 30_000_000_000

    # Optional known relationship between one source-clock unit
    # and reference nanoseconds.
    #
    # Examples:
    #   milliseconds -> 1_000_000
    #   microseconds -> 1_000
    #   nanoseconds  -> 1
    nominal_scale_ns_per_source_unit: float | None = None

    # Seed the bounded tracking window once at alignment, without re-observing.
    reuse_calibration_history: bool = False
