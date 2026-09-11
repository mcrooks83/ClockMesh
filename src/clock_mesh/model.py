"""Affine clock-domain model."""

from __future__ import annotations

from .config import ClockAlignmentConfig
from .types import ClockModelState


class AffineClockModel:
    """Learn and apply an affine mapping between two clock domains.

    Mapping:

        reference_time = a * source_time + b
    """

    def __init__(
        self,
        config: ClockAlignmentConfig | None = None,
    ) -> None:
        self.config = config or ClockAlignmentConfig()

        self.state = ClockModelState.UNOBSERVED
        self.observation_count = 0

        self._anchor_source_time: int | float | None = None
        self._anchor_reference_time_ns: int | None = None

        self._estimated_scale_ns_per_source_unit: float | None = None

    @property
    def mapping_available(self) -> bool:
        """Return whether the model can currently map source timestamps."""
        return (
            self._anchor_source_time is not None
            and self._anchor_reference_time_ns is not None
            and self.config.nominal_scale_ns_per_source_unit is not None
        )

    @property
    def estimated_scale_ns_per_source_unit(self) -> float | None:
        """Return the current learned scale estimate, if available."""
        return self._estimated_scale_ns_per_source_unit

    def observe(
        self,
        source_time: int | float,
        reference_time_ns: int,
    ) -> None:
        """Add one observed correspondence between the two clocks."""

        self.observation_count += 1

        if self.observation_count == 1:
            self._anchor_source_time = source_time
            self._anchor_reference_time_ns = reference_time_ns
            self.state = ClockModelState.ANCHORED
            return

        if self.observation_count == 2:
            assert self._anchor_source_time is not None
            assert self._anchor_reference_time_ns is not None

            source_delta = source_time - self._anchor_source_time
            reference_delta_ns = (
                reference_time_ns - self._anchor_reference_time_ns
            )

            if source_delta == 0:
                return

            self._estimated_scale_ns_per_source_unit = (
                reference_delta_ns / source_delta
            )

            self.state = ClockModelState.RATE_ESTIMATING

    def map(self, source_time: int | float) -> int | None:
        """Map a source timestamp onto the reference clock."""

        if not self.mapping_available:
            return None

        assert self._anchor_source_time is not None
        assert self._anchor_reference_time_ns is not None
        assert self.config.nominal_scale_ns_per_source_unit is not None

        source_delta = source_time - self._anchor_source_time

        return round(
            self._anchor_reference_time_ns
            + source_delta * self.config.nominal_scale_ns_per_source_unit
        )