"""Calibration pairs seed the candidate once; new pairs extend the same fit."""

from dataclasses import replace

import pytest

from clock_mesh import AffineClockModel, ClockAlignmentConfig, ClockModelState


def history_config(**overrides):
    return ClockAlignmentConfig(**{
        "target_calibration_span_ns": 1_000_000_000,
        "min_tracking_acceptance_span_ns": 5_000_000_000,
        "reuse_calibration_history": True,
        **overrides,
    })


def test_one_second_alignment_five_second_candidate_uses_every_pair_once():
    model = AffineClockModel(history_config())
    pairs = []
    for i in range(301):
        source = round(i * 1_000_000 / 60)
        # Early curvature gives the initial second a different relationship
        # from the later pairs, so fitting only post-alignment data is detectable.
        reference = 10_000_000_000 + source * 1000 + max(60 - i, 0) ** 2 * 1000
        pairs.append((source, reference))
        model.observe(source, reference)
        assert model.observation_count == len(pairs)
        if i < 61:
            # Curvature makes the first exact one-second source point's
            # reference span slightly shorter than one second.
            assert not model.mapping_available
        if model.mapping_available:
            assert model.retained_tracking_observation_count == len(pairs)
            assert model.retained_tracking_reference_span_ns == reference - pairs[0][1]
        assert not model.candidate_is_eligible(source)  # span still under five seconds
    source = round(301 * 1_000_000 / 60)
    reference = 10_000_000_000 + source * 1000
    pairs.append((source, reference))
    model.observe(source, reference)
    assert model.candidate_is_eligible(source)
    assert model.retained_tracking_observation_count == model.observation_count == 302
    assert model.retained_tracking_reference_span_ns == reference - pairs[0][1]
    # Independent OLS over ALL unique input pairs, including the first second.
    xs = [s - pairs[0][0] for s, _ in pairs]
    ys = [r - pairs[0][1] for _, r in pairs]
    x_mean, y_mean = sum(xs) / len(xs), sum(ys) / len(ys)
    scale = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / sum(
        (x - x_mean) ** 2 for x in xs)
    expected = pairs[0][1] + round(y_mean + (source - pairs[0][0] - x_mean) * scale)
    assert model.candidate_scale_ns_per_source_unit == pytest.approx(scale, abs=1e-10)
    assert model.map_candidate(source) == expected
    provisional = model.map(source)
    assert provisional != expected
    assert model.accept_full_candidate(source)
    assert model.map(source) == expected
    next_source = source + 16_667
    before = model.map(next_source)
    model.observe(next_source, reference + 16_667_000)
    assert model.observation_count == 303
    assert model.accept_candidate(next_source)
    assert model.map(next_source) == before


def test_alignment_pair_is_seeded_once_without_tracking_error_or_extra_observation():
    model = AffineClockModel(history_config())
    for i in range(61):
        model.observe(i * 50_000, 2_000_000_000 + i * 50_000_000)
        if i == 20:
            assert model.state is ClockModelState.ALIGNED
            assert model.observation_count == model.retained_tracking_observation_count == 21
            assert model.retained_tracking_reference_span_ns == 1_000_000_000
            assert model.recent_prediction_errors_ns == ()
            assert not model.candidate_is_eligible(i * 50_000)
        if i > 20:
            assert len(model.recent_prediction_errors_ns) == i - 20
            assert model.retained_tracking_observation_count == i + 1
    assert model.retained_observation_count == 21


def test_seed_and_subsequent_window_are_bounded_and_report_actual_span():
    model = AffineClockModel(history_config(max_tracking_observations=5))
    for i in range(61):
        model.observe(i * 50_000, 2_000_000_000 + i * 50_000_000)
    assert model.observation_count == 61
    assert model.retained_tracking_observation_count == 5
    assert model.retained_tracking_reference_span_ns == 200_000_000
    assert not model.candidate_is_eligible(60 * 50_000)


def test_legacy_default_keeps_calibration_and_tracking_windows_separate():
    model = AffineClockModel(replace(history_config(), reuse_calibration_history=False))
    for i in range(21):
        model.observe(i * 50_000, 2_000_000_000 + i * 50_000_000)
    assert model.state is ClockModelState.ALIGNED
    assert model.retained_tracking_observation_count == 0
    assert model.retained_tracking_reference_span_ns is None
    assert model.map_candidate(1_000_000) is None
    model.observe(1_050_000, 3_050_000_000)
    assert model.retained_tracking_observation_count == 1
    assert model.retained_tracking_reference_span_ns == 0
