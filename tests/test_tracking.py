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