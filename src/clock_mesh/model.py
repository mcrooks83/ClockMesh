"""Affine clock-domain model."""

from __future__ import annotations
from collections import deque

from .config import ClockAlignmentConfig
from .types import ClockModelState, ClockObservation, ClockObservation


class AffineClockModel:
    """
    Learn and apply an affine mapping between two clock domains.
    Mapping:  reference_time = a * source_time + b
    """

    def __init__(
        self,
        config: ClockAlignmentConfig | None = None,
    ) -> None:
        self.config = config or ClockAlignmentConfig()

        # set the initial clock model state and observation count
        self.state = ClockModelState.UNOBSERVED

        # container to hold observations.
        self._observation_count = 0

        self._observations: deque[ClockObservation] = deque(
            maxlen=self.config.max_calibration_observations,
        )
        self._retained_observations: list[ClockObservation] = []

        # preserverd for previous tests
        self._anchor_source_time: int | float | None = None
        self._anchor_reference_time_ns: int | None = None

        self._estimated_scale_ns_per_source_unit: float | None = None

        self._fit_source_anchor: int | float | None = None
        self._fit_reference_anchor_ns: int | None = None
        self._fit_reference_offset_ns: float | None = None

        self._last_prediction_error_ns: int | None = None
        self._tracking_errors_ns: deque[int] = deque(
            maxlen=self.config.max_tracking_errors,
        )

    @property
    def prediction_error_stddev_ns(self) -> float | None:
        """Return the standard deviation of retained tracking errors."""
        if not self._tracking_errors_ns:
            return None

        mean = self.mean_prediction_error_ns
        assert mean is not None

        variance = sum(
            (error - mean) ** 2 for error in self._tracking_errors_ns
        ) / len(self._tracking_errors_ns)

        return variance**0.5
    
    @property
    def mean_prediction_error_ns(self) -> float | None:
        """Return the mean signed error over the retained tracking window."""
        if not self._tracking_errors_ns:
            return None

        return sum(self._tracking_errors_ns) / len(self._tracking_errors_ns)

    @property
    def recent_prediction_errors_ns(self) -> tuple[int, ...]:
        """Return retained tracking errors, oldest to newest."""
        return tuple(self._tracking_errors_ns)

    @property
    def retained_observation_count(self) -> int:
        """Return the number of calibration observations retained."""
        return len(self._observations)
    
    @property
    def last_prediction_error_ns(self) -> int | None:
        """Return the prediction error from the most recent observation."""
        return self._last_prediction_error_ns   

    @property
    def observation_count(self) -> int:
        return self._observation_count

    @property
    def mapping_available(self) -> bool:
        """Return whether the model can currently map source timestamps."""

        # can we learn a mapping from the observations?
        learned_mapping_available = (
            self.state in {
                ClockModelState.ALIGNED,
                ClockModelState.TRACKING,
            }

            and self._fit_source_anchor is not None
            and self._fit_reference_anchor_ns is not None
            and self._fit_reference_offset_ns is not None
            and self._estimated_scale_ns_per_source_unit is not None

        )

        if learned_mapping_available:
            return True

        # why do this? it is either available or not?
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

        self._observation_count += 1

        # Tracking evaluates the observation without adding calibration data.
        if self.state in {
            ClockModelState.ALIGNED,
            ClockModelState.TRACKING,
        }:
            predicted_reference_ns = self.map(source_time)
            assert predicted_reference_ns is not None

            self._last_prediction_error_ns = (
                reference_time_ns - predicted_reference_ns
            )

            self._tracking_errors_ns.append(self._last_prediction_error_ns)

            self.state = ClockModelState.TRACKING
            return

        self._observations.append(
            ClockObservation(
                source_time=source_time,
                reference_time_ns=reference_time_ns,
            )
        )

        if self.observation_count == 1:
            self._anchor_source_time = source_time
            self._anchor_reference_time_ns = reference_time_ns
            self.state = ClockModelState.ANCHORED
            return

        # Existing calibration fit code continues here:
        scale, _ = self._calculate_affine_fit()

        scale, _ = self._calculate_affine_fit()

        if scale is not None:
            self._estimated_scale_ns_per_source_unit = scale
            self.state = ClockModelState.RATE_ESTIMATING

        # check if enough evidence has been observed to promote the current fit to an applied mapping.
        # this is where the model transitions from RATE_ESTIMATING to ALIGNED.
        if self._ready_to_align():
            self._accept_learned_mapping()

    def map(self, source_time: int | float) -> int | None:
        """Map a source timestamp onto the reference clock."""
 
        if not self.mapping_available:
            return None

        if (
            self.state in {
                ClockModelState.ALIGNED,
                ClockModelState.TRACKING,
            }
            and self._fit_source_anchor is not None
            and self._fit_reference_anchor_ns is not None
            and self._fit_reference_offset_ns is not None
            and self._estimated_scale_ns_per_source_unit is not None
        ):

            source_delta = source_time - self._fit_source_anchor
            mapped_delta_ns = (
                self._fit_reference_offset_ns
                + source_delta * self._estimated_scale_ns_per_source_unit
            )

            return self._fit_reference_anchor_ns + round(mapped_delta_ns)


        assert self._anchor_source_time is not None
        assert self._anchor_reference_time_ns is not None
        assert self.config.nominal_scale_ns_per_source_unit is not None
 
        source_delta = source_time - self._anchor_source_time
 
        return round(
            self._anchor_reference_time_ns
            + source_delta * self.config.nominal_scale_ns_per_source_unit
        )

    def _ready_to_align(self) -> bool:
        """Return whether enough calibration evidence has been observed."""

        if (
            self.retained_observation_count
            < self.config.min_learned_observations
        ):
            return False

        first_reference_ns = self._observations[0].reference_time_ns
        latest_reference_ns = self._observations[-1].reference_time_ns
        reference_span_ns = latest_reference_ns - first_reference_ns

        return reference_span_ns >= self.config.target_calibration_span_ns


    def _accept_learned_mapping(self) -> None:
        """Promote the current affine estimate to an applied mapping."""

        scale, offset_ns = self._calculate_affine_fit()
        if scale is None or offset_ns is None:
            return

        anchor = self._observations[0]
        self._estimated_scale_ns_per_source_unit = scale
        self._fit_source_anchor = anchor.source_time
        self._fit_reference_anchor_ns = anchor.reference_time_ns
        self._fit_reference_offset_ns = offset_ns
        self.state = ClockModelState.ALIGNED
 
    def _calculate_affine_fit(
        self,
    ) -> tuple[float | None, float | None]:
        """Estimate scale and offset with centred ordinary least squares.

        The fit is performed on deltas from the first observation:

            reference_delta = scale * source_delta + offset

        This avoids regressing directly against large absolute timestamps.

        """

        if self.retained_observation_count < 2:
            return None, None

        anchor = self._observations[0]

        source_deltas = [
            float(observation.source_time - anchor.source_time)
            for observation in self._observations
        ]

        reference_deltas = [
            float(
                observation.reference_time_ns
                - anchor.reference_time_ns
            )
            for observation in self._observations
        ]


        mean_source = sum(source_deltas) / len(source_deltas)
        mean_reference = sum(reference_deltas) / len(reference_deltas)


        denominator = sum(
            (source_delta - mean_source) ** 2
            for source_delta in source_deltas
        )

        if denominator == 0:
            return None, None

        numerator = sum(
            (source_delta - mean_source)
            * (reference_delta - mean_reference)
            for source_delta, reference_delta in zip(
                source_deltas,
                reference_deltas,
            )
        )

        scale = numerator / denominator
        offset_ns = mean_reference - scale * mean_source

        return scale, offset_ns