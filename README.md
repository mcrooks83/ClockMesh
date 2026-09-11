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
