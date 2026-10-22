"""Affine clock-domain model."""

from __future__ import annotations
from collections import deque
import math

from .config import ClockAlignmentConfig
from .types import ClockModelState, ClockObservation, ClockObservation


class AffineClockModel:
    """Learn an affine mapping from source units to reference nanoseconds.

    The relationship is ``reference_time_ns = scale * source_time + offset``.
    Initial calibration applies a learned mapping automatically once its count
    and reference-span thresholds are met. Later observations produce a separate
    candidate; callers explicitly choose full-affine or continuous-scale acceptance.

    Each instance represents one continuous clock relationship. Callers must
    handle invalid timestamp pairs, rollover, resets, and epoch boundaries.
    Alignment state describes model maturity, not fit quality or synchronization
    accuracy. Observation windows and error statistics are bounded by config.
    """

    def __init__(
        self,
        config: ClockAlignmentConfig | None = None,
    ) -> None:
        """Create an unobserved model with empty observation and error windows.

        Args:
            config: Calibration, tracking, storage, and optional nominal-scale
                settings. If omitted, use ClockAlignmentConfig defaults.

        No timestamp is mapped until a first pair anchors a configured nominal
        scale, or enough calibration evidence establishes a learned mapping.
        """
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

        self._tracking_observations: deque[ClockObservation] = deque(
            maxlen=self.config.max_tracking_observations,
        )

        self._candidate_scale_ns_per_source_unit: float | None = None
        self._candidate_reference_offset_ns: float | None = None

    @property
    def retained_tracking_observation_count(self) -> int:
        """Return the number of pairs in the bounded candidate-fit window.

        Includes seeded calibration pairs when history reuse is enabled. This
        count is independent of the tracking-error window and total observations.
        """
        return len(self._tracking_observations)

    @property
    def retained_tracking_reference_span_ns(self) -> int | None:
        """Return last-minus-first reference time in the candidate-fit window.

        The span is in nanoseconds, includes seeded calibration pairs, and
        describes the retained window rather than total capture duration. Return
        None for an empty window and zero for a single pair.
        """
        if not self._tracking_observations:
            return None
        return (self._tracking_observations[-1].reference_time_ns
                - self._tracking_observations[0].reference_time_ns)

    @property
    def candidate_scale_ns_per_source_unit(self) -> float | None:
        """Return the latest candidate slope in nanoseconds per source unit.

        Return None when no candidate slope can be fitted. Reading this value
        neither accepts the candidate nor establishes its eligibility.
        """
        return self._candidate_scale_ns_per_source_unit

    @property
    def prediction_error_stddev_ns(self) -> float | None:
        """Return the population standard deviation of retained tracking errors.

        Values are in nanoseconds. Return None before any tracking errors exist;
        a single retained error has zero standard deviation.
        """
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
        """Return the signed mean of retained tracking errors, in nanoseconds.

        Error is observed reference time minus the accepted mapping evaluated
        before candidate acceptance. Return None when the error window is empty.
        """
        if not self._tracking_errors_ns:
            return None

        return sum(self._tracking_errors_ns) / len(self._tracking_errors_ns)

    @property
    def recent_prediction_errors_ns(self) -> tuple[int, ...]:
        """Return an immutable snapshot of tracking errors, oldest to newest.

        Errors are in nanoseconds and are limited by max_tracking_errors.
        Calibration pairs copied into tracking storage do not create errors.
        """
        return tuple(self._tracking_errors_ns)

    @property
    def retained_observation_count(self) -> int:
        """Return the number of retained initial-calibration timestamp pairs.

        Limited by max_calibration_observations. Tracking does not append to this
        window; history reuse copies its pairs into the candidate-fit window once.
        """
        return len(self._observations)
    
    @property
    def last_prediction_error_ns(self) -> int | None:
        """Return the most recent tracking error in reference nanoseconds.

        Positive means the observed reference was later than the accepted mapping
        predicted. Return None until the first observation after initial alignment.
        Later candidate acceptance does not recompute this stored error.
        """
        return self._last_prediction_error_ns   

    @property
    def observation_count(self) -> int:
        """Return the total number of observe() calls for this model instance.

        Includes calibration and tracking pairs, even those evicted from bounded
        storage. Seeding the tracking window does not increment this count.
        """
        return self._observation_count

    @property
    def mapping_available(self) -> bool:
        """Return whether map() can use a learned or nominal-scale mapping.

        A learned mapping requires ALIGNED or TRACKING state and an applied fit.
        A configured nominal scale permits mapping after the first anchor pair,
        before learned alignment. Availability is not a fit-quality assessment.
        """

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
        """Return the learned slope estimate, or None before one can be fitted.

        Units are reference nanoseconds per source unit. During calibration this
        is a provisional estimate; in ALIGNED/TRACKING it is the applied scale.
        Later unaccepted candidate slopes are exposed separately.
        """
        return self._estimated_scale_ns_per_source_unit

    def observe(
        self,
        source_time: int | float,
        reference_time_ns: int,
    ) -> None:
        """Supply one timestamp correspondence and advance calibration or tracking.

        Args:
            source_time: Timestamp in the caller's consistent source-clock units.
            reference_time_ns: Corresponding integer reference-clock nanoseconds.

        The first pair anchors the model. Further calibration pairs estimate the
        rate and automatically establish ALIGNED once the retained count and
        reference span meet config thresholds. If history reuse is enabled, those
        pairs seed the bounded candidate-fit window once, without extra counts
        or prediction errors.

        After alignment, evaluate error against the applied mapping, append this
        pair once to the tracking window, refit the candidate, and enter TRACKING.
        The applied mapping stays unchanged until a caller accepts a candidate.

        The caller supplies valid, continuous pairs. This method does not reject
        outliers, unwrap timestamps, or enforce calibration_deadline_ns.
        """

        self._observation_count += 1

        # Tracking evaluates the observation without adding calibration data.
        if self.state in {
            ClockModelState.ALIGNED,
            ClockModelState.TRACKING,
        }:
            # Evaluate against the accepted mapping before calculating a candidate.
            predicted_reference_ns = self.map(source_time)
            assert predicted_reference_ns is not None

            self._last_prediction_error_ns = (
                reference_time_ns - predicted_reference_ns
            )
            self._tracking_errors_ns.append(self._last_prediction_error_ns)

            self._tracking_observations.append(
                ClockObservation(
                    source_time=source_time,
                    reference_time_ns=reference_time_ns,
                )
            )

            scale, offset_ns = self._calculate_affine_fit(
                self._tracking_observations
            )

            self._candidate_scale_ns_per_source_unit = scale
            self._candidate_reference_offset_ns = offset_ns

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
        scale, _ = self._calculate_affine_fit(self._observations)

        if scale is not None:
            self._estimated_scale_ns_per_source_unit = scale
            self.state = ClockModelState.RATE_ESTIMATING

        # check if enough evidence has been observed to promote the current fit to an applied mapping.
        # this is where the model transitions from RATE_ESTIMATING to ALIGNED.
        if self._ready_to_align():
            self._accept_learned_mapping()

    def map_candidate(self, source_time: int | float) -> int | None:
        """Predict reference nanoseconds using the latest full candidate fit.

        Args:
            source_time: Timestamp in the same source units used by observe().

        Returns:
            Integer reference nanoseconds, rounding the fitted delta relative to
            the window's first pair, or None if no candidate fit is available.

        Does not accept the fit or require acceptance eligibility. With history
        reuse, a candidate can be available immediately at initial alignment.
        """
        if (
            not self._tracking_observations
            or self._candidate_scale_ns_per_source_unit is None
            or self._candidate_reference_offset_ns is None
        ):
            return None

        anchor = self._tracking_observations[0]
        source_delta = source_time - anchor.source_time

        mapped_delta_ns = (
            self._candidate_reference_offset_ns
            + source_delta * self._candidate_scale_ns_per_source_unit
        )

        return anchor.reference_time_ns + round(mapped_delta_ns)

    def map(self, source_time: int | float) -> int | None:
        """Map a source timestamp with the currently applied clock relationship.

        Args:
            source_time: Timestamp in the same source units used by observe().

        Returns:
            Integer reference nanoseconds, or None if no mapping is available.
            The result uses the applied learned fit when aligned; otherwise it
            uses the first anchor and configured nominal scale, if available.

        Does not observe the timestamp or use an unaccepted tracking candidate.
        Learned-fit deltas are rounded before adding the integer reference anchor.
        """
 
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
        """Check initial-calibration count and reference-span thresholds.

        Both thresholds use retained calibration pairs. The span is the last
        reference timestamp minus the first, in nanoseconds, and equality meets
        target_calibration_span_ns. Does not enforce a deadline or assess quality.
        """

        if (
            self.retained_observation_count
            < self.config.min_learned_observations
        ):
            return False

        first_reference_ns = self._observations[0].reference_time_ns
        latest_reference_ns = self._observations[-1].reference_time_ns
        reference_span_ns = latest_reference_ns - first_reference_ns

        return reference_span_ns >= self.config.target_calibration_span_ns

    def candidate_is_eligible(self, source_time: int | float) -> bool:
        """Check whether a tracking candidate may be accepted at this pivot.

        Args:
            source_time: Proposed acceptance pivot in source-clock units.

        Requires TRACKING state, at least min_learned_observations retained pairs,
        at least min_tracking_acceptance_span_ns of reference history, a finite
        positive candidate slope, and a pivot equal to the latest observed source
        timestamp. Seeded calibration pairs contribute to count and span.

        Returns a boolean without changing model state or the applied mapping.
        An eligible candidate need not fill the window to its storage capacity.
        """
        if self.state is not ClockModelState.TRACKING:
            return False

        if (
            len(self._tracking_observations)
            < self.config.min_learned_observations
        ):
            return False

        first = self._tracking_observations[0]
        latest = self._tracking_observations[-1]

        reference_span_ns = (
            latest.reference_time_ns - first.reference_time_ns
        )

        if (
            reference_span_ns
            < self.config.min_tracking_acceptance_span_ns
        ):
            return False

        scale = self._candidate_scale_ns_per_source_unit
        if scale is None or not math.isfinite(scale) or scale <= 0:
            return False

        # Accept only at the latest observed source timestamp.
        if source_time != latest.source_time:
            return False

        return True

    def accept_full_candidate(self, source_time: int | float) -> bool:
        """Apply candidate scale and offset at the latest observed source pivot.

        Args:
            source_time: Latest observed source timestamp, in source-clock units.

        Returns:
            True if eligible and applied; False without changing the mapping if
            eligibility fails or the candidate cannot map the pivot.

        Re-anchor the applied mapping at the candidate's rounded reference time
        for this pivot and use its slope thereafter. This can change mapped time
        at the boundary. It does not clear observation history or stored errors.
        Use accept_candidate() when the pivot's mapped time must stay continuous.
        """
        if not self.candidate_is_eligible(source_time):
            return False
        mapped_time_ns = self.map_candidate(source_time)
        if mapped_time_ns is None:
            return False
        self._fit_source_anchor = source_time
        self._fit_reference_anchor_ns = mapped_time_ns
        self._fit_reference_offset_ns = 0.0
        self._estimated_scale_ns_per_source_unit = self._candidate_scale_ns_per_source_unit
        return True

    def accept_candidate(self, source_time: int | float) -> bool:
        """Apply the candidate slope while preserving mapped time at the pivot.

        Args:
            source_time: Latest observed source timestamp, in source-clock units.

        Returns:
            True if eligible and applied; False without changing the mapping if
            eligibility fails or the current mapping cannot map the pivot.

        Re-anchor at the current mapped reference time and replace only the
        slope. The mapped pivot is preserved exactly; candidate offset is not
        applied. Observation history and stored prediction errors are unchanged.
        """
        if not self.candidate_is_eligible(source_time):
            return False
        scale = self._candidate_scale_ns_per_source_unit
        mapped_time_ns = self.map(source_time)
        if mapped_time_ns is None:
            return False

        # Preserve the current mapped time and change the slope from here.
        self._fit_source_anchor = source_time
        self._fit_reference_anchor_ns = mapped_time_ns
        self._fit_reference_offset_ns = 0.0
        self._estimated_scale_ns_per_source_unit = scale

        return True

    def _accept_learned_mapping(self) -> None:
        """Apply the retained calibration fit and enter ALIGNED if it exists.

        Anchor scale and offset relative to the first retained calibration pair.
        The caller checks calibration readiness before invoking this helper.
        When reuse_calibration_history is enabled, seed the bounded tracking
        window once and fit its candidate without observing the pairs again.
        Leave the mapping unchanged if the calibration fit cannot be calculated.
        """

        scale, offset_ns = self._calculate_affine_fit(self._observations)
        if scale is None or offset_ns is None:
            return

        anchor = self._observations[0]
        self._estimated_scale_ns_per_source_unit = scale
        self._fit_source_anchor = anchor.source_time
        self._fit_reference_anchor_ns = anchor.reference_time_ns
        self._fit_reference_offset_ns = offset_ns
        self.state = ClockModelState.ALIGNED
        if self.config.reuse_calibration_history:
            # The alignment pair is already in calibration storage. Transfer
            # once without observe(), so counts/errors and pair weights stay intact.
            self._tracking_observations.extend(self._observations)
            scale, offset_ns = self._calculate_affine_fit(self._tracking_observations)
            self._candidate_scale_ns_per_source_unit = scale
            self._candidate_reference_offset_ns = offset_ns
 
    @staticmethod
    def _calculate_affine_fit(
        observations: list[ClockObservation] | deque[ClockObservation],
    ) -> tuple[float | None, float | None]:
        """Fit reference deltas against source deltas by ordinary least squares.

        Args:
            observations: Ordered timestamp pairs in caller-defined source units
                and integer reference nanoseconds. The first pair is the anchor.

        Returns:
            (scale, offset_ns), where scale is nanoseconds per source unit and
            offset_ns is relative to the first pair's reference timestamp at its
            source timestamp, not a global intercept. Return (None, None) for
            fewer than two pairs or zero variance in source timestamps.

        Subtract anchors before floating-point fitting to reduce loss of precision
        from large absolute timestamps. Every supplied pair has equal weight;
        no outlier rejection or sign/finite-value eligibility checks occur here.
        """
        if len(observations) < 2:
            return None, None

        anchor = observations[0]

        source_deltas = [
            float(observation.source_time - anchor.source_time)
            for observation in observations
        ]

        reference_deltas = [
            float(
                observation.reference_time_ns
                - anchor.reference_time_ns
            )
            for observation in observations
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