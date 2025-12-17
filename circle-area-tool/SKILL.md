---
name: circle-area-tool
description: Compute the area within a round circle (disk) given its radius. Provides a reliable, high-precision Python script (scripts/circle_area.py) that validates input and outputs the area. Use when asked to calculate the area of a circle/disk from radius, check corner cases (zero, negative, non-numeric, very large/small), or run quick numeric tests.
---

# Circle Area Tool

## Overview

This skill computes the area inside a circle from its radius using high-precision Decimal arithmetic. It includes a CLI script and a small testing harness.

## Quick Start

- Primary script: scripts/circle_area.py
- Purpose: Compute area A = π × r^2 with robust input validation
- Precision: Decimal arithmetic with configurable significant digits

### CLI usage

- Positional radius: scripts/circle_area.py <radius>
- Or explicit: scripts/circle_area.py --radius <radius>
- Optional: --precision <int> (significant digits, default: 50)
- Output format: JSON by default; use --output text for plain text.

Examples:
- scripts/circle_area.py 3
- scripts/circle_area.py --radius 2.5 --precision 40

### Behavior
- Accepts integers, decimals, scientific notation (e.g., 1e-5)
- Rejects negative, NaN, or infinite values
- Returns JSON: { "radius": str, "area": str, "precision": int }

## Testing

- Test harness: scripts/run_tests.py
- Runs representative and edge-case tests, printing a JSON summary of pass/fail.

## Notes
- π is computed from a high-precision constant string to avoid float limitations.
- Computation uses Decimal with a safety margin beyond requested precision to reduce rounding propagation.
