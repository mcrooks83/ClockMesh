"""Affine clock-domain model."""

from __future__ import annotations

from .config import ClockAlignmentConfig
from .types import ClockModelState


class AffineClockModel:
    """Learn and apply an affine mapping between two clock domains.

    Mapping:

        reference_time = a * source_time + b

    Implementation will be developed test-first.
    """

    def __init__(
        self,
        config: ClockAlignmentConfig | None = None,
    ) -> None:
        self.config = config or ClockAlignmentConfig()
        self.state = ClockModelState.UNOBSERVED

    def observe(
        self,
        source_time: int | float,
        reference_time_ns: int,
    ) -> None:
        raise NotImplementedError

    def map(self, source_time: int | float) -> int | None:
        raise NotImplementedError
