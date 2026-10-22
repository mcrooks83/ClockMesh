# ClockMesh

Generic clock-domain alignment library.

The library learns relationships between independent clock domains from
timestamp observation pairs.

Conceptually:

    source timestamp <-> reference timestamp

Repeated observations allow an affine relationship to be estimated:

    reference_time = a * source_time + b

The library is deliberately independent of Nexus N3, sensors, BLE, cameras,
sessions, and acquisition frameworks.

## Initial design goals

- Preserve source timestamps.
- Map independent clocks onto a reference clock.
- Support unknown and optionally known source clock scales.
- Support sources with different observation rates.
- Separate model maturity from fit quality.
- Target useful calibration after approximately 2 seconds.
- Target learned alignment after approximately 2 seconds and resolve the mapping strategy within 5 seconds.
- Later support jitter, outliers, drift and clock epochs.

## Development approach

The implementation is test-driven.

Initial stages:

1. UNOBSERVED
2. ANCHORED
3. RATE_ESTIMATING
4. ALIGNED
5. TRACKING

Tests define the expected behaviour before implementation.

## Candidate acceptance

After initial alignment, tracking observations produce a separate affine candidate.
`candidate_is_eligible(source_time)` exposes the existing acceptance checks:
tracking state, minimum observation count and reference span, finite positive scale,
and a pivot equal to the latest observed source timestamp.

`accept_candidate(source_time)` changes scale while preserving mapped time exactly
at the pivot. Its continuous-update behavior is unchanged.
`accept_full_candidate(source_time)` uses the same eligibility checks and applies
both candidate scale and offset, anchored at that pivot. This explicit phase-boundary
operation can change mapped time; it returns false without changing the mapping
when the candidate is ineligible. Callers decide when a phase boundary is appropriate.

## Continuous calibration and candidate history

`ClockAlignmentConfig(reuse_calibration_history=True)` seeds the bounded tracking
window with the retained calibration observations once, when initial alignment is
established. The alignment observation is included once. This transfer does not
call `observe()` again, increment `observation_count`, or add tracking errors.
Subsequent observations append normally; candidate eligibility and both acceptance
methods use the same window. `retained_tracking_observation_count` and
`retained_tracking_reference_span_ns` report that window's actual count and span.
The tracking capacity still bounds storage; old pairs expire as it fills.

For one-second provisional alignment and a full candidate after five seconds total,
set `target_calibration_span_ns=1000000000`,
`min_tracking_acceptance_span_ns=5000000000`, and `reuse_calibration_history=True`.
At 60 Hz with adequate capacity, the five-second candidate uses all 301 pairs,
including those used for initial alignment. The reuse flag defaults to `False` to
preserve existing callers' separate calibration and tracking histories.
