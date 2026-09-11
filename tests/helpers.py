"""Synthetic clock helpers used by clock-alignment tests.

This module will provide deterministic clocks with configurable:

- source origin
- source units
- observation rate
- clock-rate difference
- jitter
- outliers
- drift
- resets

The helper should describe known ground truth so model output can be
compared directly against the expected reference timeline.
"""
