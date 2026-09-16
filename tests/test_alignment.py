"""Tests for promotion to an aligned clock model."""

import pytest

from clock_mesh import AffineClockModel, ClockModelState 

# first test, perfect 60hz clock, promote to aling
def test_60hz_unknown_scale_clock_aligns_after_two_seconds() -> None:
    model = AffineClockModel()

    # starting point 
    source_start = 32_000_000.0 # micro
    reference_start_ns = 50_000_000_000 # nano

    # rules:
    # ClockMesh is not told the source units. The synthetic relationship is:
    #     1 source unit = 1,000 reference nanoseconds
    # 121 observations give 120 intervals at 60 Hz = exactly 2 seconds.
    for index in range(121):
        elapsed_s = index / 60.0
 
        source_time = source_start + elapsed_s * 1_000_000
        reference_time_ns = (
            reference_start_ns
            + round(elapsed_s * 1_000_000_000)
        )
 
        model.observe(
            source_time=source_time,
            reference_time_ns=reference_time_ns,
        )

    # tests 
    assert model.state is ClockModelState.ALIGNED
    assert model.observation_count == 121
    assert model.mapping_available is True
 
    assert model.estimated_scale_ns_per_source_unit == pytest.approx(
        1_000.0,
        rel=1e-9,
    )
 
    mapped_time = model.map(34_000_000.0)
 
    assert mapped_time is not None
    assert mapped_time == pytest.approx(
        52_000_000_000,
        abs=2,
    )


