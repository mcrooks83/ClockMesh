"""Tests for clock-model tracking after initial alignment."""

import pytest

from clock_mesh import AffineClockModel, ClockModelState, ClockAlignmentConfig


# helper function to create an aligned model for testing.
def make_aligned_model(
        config: ClockAlignmentConfig | None = None,
) -> AffineClockModel:
    model = AffineClockModel(config=config)

    for index in range(121):
        model.observe(
            source_time=32_000_000 + index * 1_000_000 / 60,
            reference_time_ns=(
                50_000_000_000
                + round(index * 1_000_000_000 / 60)
            ),
        )

    assert model.state is ClockModelState.ALIGNED
    return model


def test_aligned_model_begins_tracking_on_next_observation() -> None:
    model = make_aligned_model()

    mapped_before = model.map(35_000_000)
    assert mapped_before is not None

    model.observe(
        source_time=35_000_000,
        reference_time_ns=53_000_000_000,
    )

    assert model.state is ClockModelState.TRACKING
    assert model.observation_count == 122
    assert model.mapping_available is True
    assert model.map(35_000_000) == mapped_before


def test_tracking_records_prediction_error_without_changing_mapping() -> None:
    model = make_aligned_model()

    # An observation following the learned relationship has near-zero error.
    model.observe(
        source_time=35_000_000,
        reference_time_ns=53_000_000_000,
    )

    assert model.last_prediction_error_ns == pytest.approx(0, abs=2)

    predicted_reference_ns = model.map(36_000_000)
    assert predicted_reference_ns is not None

    # Introduce an observation 5 ms later than predicted.
    model.observe(
        source_time=36_000_000,
        reference_time_ns=predicted_reference_ns + 5_000_000,
    )

    assert model.state is ClockModelState.TRACKING
    assert model.last_prediction_error_ns == 5_000_000
    assert model.map(36_000_000) == predicted_reference_ns

def test_prediction_error_is_none_before_tracking() -> None:
    assert AffineClockModel().last_prediction_error_ns is None

    model = make_aligned_model()
    assert model.last_prediction_error_ns is None

def test_tracking_replaces_previous_prediction_error() -> None:
    model = make_aligned_model()

    # An observation following the learned relationship has near-zero error.
    model.observe(
        source_time=35_000_000,
        reference_time_ns=53_000_000_000,
    )

    assert model.last_prediction_error_ns == pytest.approx(0, abs=2)

    predicted_reference_ns = model.map(36_000_000)
    assert predicted_reference_ns is not None

    # Introduce an observation 5 ms later than predicted.
    model.observe(
        source_time=36_000_000,
        reference_time_ns=predicted_reference_ns + 5_000_000,
    )

    assert model.state is ClockModelState.TRACKING
    assert model.last_prediction_error_ns == 5_000_000
    assert model.map(36_000_000) == predicted_reference_ns

    # Calculate the prediction for the next source timestamp.
    predicted_next_ns = model.map(37_000_000)
    assert predicted_next_ns is not None

    # Introduce an observation 10 ms earlier than that prediction.
    model.observe(
        source_time=37_000_000,
        reference_time_ns=predicted_next_ns - 10_000_000,
    )

    assert model.state is ClockModelState.TRACKING
    assert model.last_prediction_error_ns == -10_000_000
    assert model.map(37_000_000) == predicted_next_ns

def test_tracking_error_window_retains_latest_errors() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(max_tracking_errors=3)
    )

    assert model.recent_prediction_errors_ns == ()

    errors_ns = (
        1_000_000,
        2_000_000,
        -3_000_000,
        4_000_000,
    )

    for index, error_ns in enumerate(errors_ns):
        source_time = 35_000_000 + index * 1_000_000
        predicted_ns = model.map(source_time)
        assert predicted_ns is not None

        model.observe(
            source_time=source_time,
            reference_time_ns=predicted_ns + error_ns,
        )

    assert model.recent_prediction_errors_ns == (
        2_000_000,
        -3_000_000,
        4_000_000,
    )
    assert model.last_prediction_error_ns == 4_000_000

def test_mean_prediction_error_uses_retained_window() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(max_tracking_errors=3)
    )

    assert model.mean_prediction_error_ns is None

    errors_ns = (
        10_000_000,
        2_000_000,
        -3_000_000,
        4_000_000,
    )

    for index, error_ns in enumerate(errors_ns):
        source_time = 35_000_000 + index * 1_000_000
        predicted_ns = model.map(source_time)
        assert predicted_ns is not None

        model.observe(
            source_time=source_time,
            reference_time_ns=predicted_ns + error_ns,
        )

    # Only the latest three errors contribute:
    # (2 ms - 3 ms + 4 ms) / 3 = +1 ms.
    assert model.mean_prediction_error_ns == pytest.approx(1_000_000)


def test_prediction_error_spread_uses_retained_window() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(max_tracking_errors=2)
    )

    assert model.prediction_error_stddev_ns is None

    for index, error_ns in enumerate(
        (20_000_000, 5_000_000, -5_000_000)
    ):
        source_time = 35_000_000 + index * 1_000_000
        predicted_ns = model.map(source_time)
        assert predicted_ns is not None

        model.observe(
            source_time=source_time,
            reference_time_ns=predicted_ns + error_ns,
        )

        # A single retained error has no spread.
        if index == 0:
            assert model.prediction_error_stddev_ns == 0

    # Only +5 ms and -5 ms remain.
    assert model.mean_prediction_error_ns == pytest.approx(0)
    assert model.prediction_error_stddev_ns == pytest.approx(5_000_000)

def test_tracking_candidate_does_not_change_accepted_mapping() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(max_tracking_observations=4)
    )

    accepted_scale = model.estimated_scale_ns_per_source_unit
    mapped_before = model.map(40_000_000)

    assert accepted_scale is not None
    assert mapped_before is not None

    # No candidate exists before tracking observations arrive.
    assert model.candidate_scale_ns_per_source_unit is None

    assert model.map_candidate(40_000_000) is None

    # Supply four observations following a slightly different relationship:
    # 1 source unit = 1,001 reference nanoseconds.
    for index in range(4):
        model.observe(
            source_time=35_000_000 + index * 1_000_000,
            reference_time_ns=(
                53_000_000_000 + index * 1_001_000_000
            ),
        )

    assert model.state is ClockModelState.TRACKING
    assert model.retained_tracking_observation_count == 4

    assert model.candidate_scale_ns_per_source_unit == pytest.approx(
        1_001.0,
        rel=1e-9,
    )

    # Extrapolate the candidate relationship by five million source units.
    assert model.map_candidate(40_000_000) == pytest.approx(
        58_005_000_000,
        abs=2,
    )

    # Calculating a candidate must leave the applied mapping unchanged.
    assert model.estimated_scale_ns_per_source_unit == accepted_scale
    assert model.map(40_000_000) == mapped_before

def test_tracking_candidate_uses_latest_observations() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(max_tracking_observations=3)
    )

    mapped_before = model.map(40_000_000)
    assert mapped_before is not None

    # This observation will be evicted from the three-pair window.
    model.observe(
        source_time=34_000_000,
        reference_time_ns=51_500_000_000,
    )

    # These three retained observations follow a scale of 1,001.
    for index in range(3):
        model.observe(
            source_time=35_000_000 + index * 1_000_000,
            reference_time_ns=(
                53_000_000_000 + index * 1_001_000_000
            ),
        )

    assert model.retained_tracking_observation_count == 3

    assert model.candidate_scale_ns_per_source_unit == pytest.approx(
        1_001.0,
        rel=1e-9,
    )

    assert model.map(40_000_000) == mapped_before

def test_accept_candidate_changes_scale_without_jump() -> None:
    model = make_aligned_model(
        config=ClockAlignmentConfig(
            max_tracking_observations=8,
            min_tracking_acceptance_span_ns=3_000_000_000,
        )
    )

    # Acceptance is unavailable before tracking.
    assert model.accept_candidate(34_000_000) is False

    # Two observations are insufficient for acceptance.
    for index in range(2):
        model.observe(
            source_time=35_000_000 + index * 1_000_000,
            reference_time_ns=(
                53_000_000_000 + index * 1_001_000_000
            ),
        )

    assert model.accept_candidate(36_000_000) is False

    # Complete five observations spanning just over four seconds.
    for index in range(2, 5):
        model.observe(
            source_time=35_000_000 + index * 1_000_000,
            reference_time_ns=(
                53_000_000_000 + index * 1_001_000_000
            ),
        )

    pivot_source = 39_000_000
    mapped_before = model.map(pivot_source)
    assert mapped_before is not None

    # Reject a pivot other than the latest observed source timestamp.
    assert model.accept_candidate(38_000_000) is False

    assert model.accept_candidate(pivot_source) is True

    assert model.state is ClockModelState.TRACKING
    assert model.estimated_scale_ns_per_source_unit == pytest.approx(
        1_001.0,
        rel=1e-9,
    )

    # No jump at acceptance.
    assert model.map(pivot_source) == mapped_before

    # Subsequent timestamps use the newly accepted scale.
    assert model.map(40_000_000) == mapped_before + 1_001_000_000

def test_full_candidate_applies_offset_and_scale_then_scale_updates_are_continuous():
    model = make_aligned_model(ClockAlignmentConfig(
        min_tracking_acceptance_span_ns=3_000_000_000))
    # Distinct slope and intercept relative to the initial calibration.
    for index in range(5):
        source = 35_000_000 + index * 1_000_000
        model.observe(source, 53_005_000_000 + index * 1_001_000_000)
    before = model.map(source)
    full = model.map_candidate(source)
    assert full != before
    assert model.candidate_is_eligible(source)
    assert not model.accept_full_candidate(source - 1)
    assert model.map(source) == before
    assert model.accept_full_candidate(source)
    assert model.map(source) == full
    assert model.estimated_scale_ns_per_source_unit == pytest.approx(1001)
    assert model.map(source + 1_000_000) == full + 1_001_000_000
    # A later candidate has a different offset and rate. Continuous acceptance
    # still preserves the current mapped pivot instead of applying that offset.
    for index in range(5):
        source = 40_000_000 + index * 1_000_000
        model.observe(source, 58_020_000_000 + index * 1_002_000_000)
    before = model.map(source)
    assert model.map_candidate(source) != before
    assert model.accept_candidate(source)
    assert model.map(source) == before


def test_full_candidate_reuses_count_and_span_eligibility():
    model = make_aligned_model(ClockAlignmentConfig(
        min_tracking_acceptance_span_ns=5_000_000_000))
    assert not model.accept_full_candidate(34_000_000)
    for index in range(6):
        source = 35_000_000 + index * 1_000_000
        model.observe(source, 53_000_000_000 + index * 1_000_000_000)
        before = model.map(source)
        assert model.candidate_is_eligible(source) == (index == 5)
        assert model.accept_full_candidate(source) == (index == 5)
        assert model.map(source) == before
