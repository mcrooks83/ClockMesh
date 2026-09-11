"""Tests for learning clock scale and offset."""

from clock_mesh import AffineClockModel, ClockModelState


def test_second_pair_enters_rate_estimation() -> None:
    model = AffineClockModel()

    model.observe(
        source_time=32_000_000,
        reference_time_ns=50_000_000_000,
    )

    model.observe(
        source_time=33_000_000,
        reference_time_ns=51_000_000_000,
    )

    assert model.state is ClockModelState.RATE_ESTIMATING
    assert model.observation_count == 2
    assert model.mapping_available is False
    assert model.estimated_scale_ns_per_source_unit == 1_000.0