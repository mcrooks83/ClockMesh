"""Tests for establishing the first clock correspondence."""

from clock_mesh import AffineClockModel, ClockModelState


def test_first_pair_anchors_unknown_scale_clock() -> None:
    model = AffineClockModel()

    model.observe(
        source_time=32_000_000,
        reference_time_ns=50_000_000_000,
    )

    assert model.state is ClockModelState.ANCHORED
    assert model.observation_count == 1
    assert model.mapping_available is False
    assert model.map(32_000_000) is None