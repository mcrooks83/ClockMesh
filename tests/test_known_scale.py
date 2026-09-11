"""Tests for sources with a supplied nominal clock scale."""

from clock_mesh import (
    AffineClockModel,
    ClockAlignmentConfig,
    ClockModelState,
)


def test_first_pair_with_known_scale_can_map() -> None:
    model = AffineClockModel(
        ClockAlignmentConfig(
            nominal_scale_ns_per_source_unit=1_000.0,
        )
    )

    model.observe(
        source_time=32_000_000,
        reference_time_ns=50_000_000_000,
    )

    assert model.state is ClockModelState.ANCHORED
    assert model.observation_count == 1
    assert model.mapping_available is True

    assert model.map(32_000_000) == 50_000_000_000
    assert model.map(33_000_000) == 51_000_000_000