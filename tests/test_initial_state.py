"""Tests for a newly created clock model."""

from clock_mesh import AffineClockModel, ClockModelState


def test_new_model_is_unobserved() -> None:
    model = AffineClockModel()

    assert model.state is ClockModelState.UNOBSERVED
