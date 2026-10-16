"""Tests for bounded clock-model observation storage."""

from clock_mesh import AffineClockModel, ClockAlignmentConfig, ClockModelState


def test_calibration_observation_storage_is_bounded() -> None:
    model = AffineClockModel(
        config=ClockAlignmentConfig(
            max_calibration_observations=8,
        )
    )

    # Ten observations span only 150 ms, so calibration is still ongoing.
    for index in range(10):
        model.observe(
            source_time=32_000_000 + index * 1_000_000 / 60,
            reference_time_ns=(
                50_000_000_000
                + round(index * 1_000_000_000 / 60)
            ),
        )

    assert model.observation_count == 10
    assert model.retained_observation_count == 8

def test_tracking_does_not_add_calibration_observations() -> None:
    model = AffineClockModel()

    for index in range(121):
        model.observe(
            source_time=32_000_000 + index * 1_000_000 / 60,
            reference_time_ns=(
                50_000_000_000
                + round(index * 1_000_000_000 / 60)
            ),
        )

    assert model.state is ClockModelState.ALIGNED
    assert model.retained_observation_count == 121

    for index in range(121, 181):
        model.observe(
            source_time=32_000_000 + index * 1_000_000 / 60,
            reference_time_ns=(
                50_000_000_000
                + round(index * 1_000_000_000 / 60)
            ),
        )

    assert model.state is ClockModelState.TRACKING
    assert model.observation_count == 181
    assert model.retained_observation_count == 121