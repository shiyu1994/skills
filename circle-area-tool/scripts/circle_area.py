#!/usr/bin/env python3
"""
Compute the area within a round circle (disk) given its radius.

Features
- High-precision Decimal arithmetic
- Validates input (non-negative, finite number)
- CLI with JSON or text output

Usage examples:
  scripts/circle_area.py 3
  scripts/circle_area.py --radius 2.5 --precision 40

Exit codes:
  0 - success
  1 - invalid input
"""

from __future__ import annotations
import argparse
import json
from decimal import Decimal, getcontext, InvalidOperation
from typing import Tuple

# High-precision value of pi (first 200 digits)
_PI_STR = (
    "3.14159265358979323846264338327950288419716939937510"
    "58209749445923078164062862089986280348253421170679"
    "82148086513282306647093844609550582231725359408128"
)

# Convert to Decimal once (with high default precision); will be rounded by context during ops
_PI_DEC = Decimal(_PI_STR)


def compute_area(radius_str: str, precision: int = 50) -> Tuple[Decimal, int]:
    """Compute area = pi * r^2 using Decimal with the requested significant digits.

    Args:
        radius_str: Radius as string (accepts scientific notation). Must be finite and >= 0.
        precision: Significant digits for computations and final rounding (>= 1).

    Returns:
        (area_decimal, precision_used)

    Raises:
        ValueError: If input is invalid (negative, NaN/Inf, non-numeric) or precision < 1
    """
    if precision is None or int(precision) < 1:
        raise ValueError("precision must be a positive integer")

    # Use a slightly higher internal precision to reduce rounding propagation
    internal_prec = int(precision) + 10
    ctx = getcontext().copy()
    ctx.prec = internal_prec

    try:
        # Parse radius using high precision context
        r = ctx.create_decimal(radius_str.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("radius must be a valid finite non-negative number")

    # Validate
    if not r.is_finite() or r.is_nan():
        raise ValueError("radius must be a valid finite non-negative number")
    if r < 0:
        raise ValueError("radius cannot be negative")

    # Compute area with internal precision, then round to requested precision via unary plus in a new context
    area = (r * r) * _PI_DEC

    # Round to requested precision (significant digits)
    round_ctx = getcontext().copy()
    round_ctx.prec = int(precision)
    area = +area  # apply current context rounding (uses global getcontext())
    # But ensure it uses round_ctx
    with round_ctx:
        area = +area

    return area, int(precision)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Compute the area inside a circle from its radius.")
    parser.add_argument("radius", nargs="?", help="Radius value (positional).", type=str)
    parser.add_argument("--radius", dest="radius_kw", help="Radius value (keyword).", type=str)
    parser.add_argument("--precision", dest="precision", help="Significant digits (default: 50)", type=int, default=50)
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")

    args = parser.parse_args()

    # Determine radius string
    r_str = args.radius_kw if args.radius_kw is not None else args.radius
    if r_str is None:
        print(json.dumps({"ok": False, "error": "radius is required"}))
        return 1

    try:
        area, prec = compute_area(r_str, precision=args.precision)
    except ValueError as e:
        if args.output == "json":
            print(json.dumps({"ok": False, "error": str(e)}))
        else:
            print(f"Error: {e}")
        return 1

    if args.output == "json":
        print(json.dumps({
            "ok": True,
            "radius": str(Decimal(r_str.strip())),
            "area": format(area, 'g'),
            "precision": prec
        }))
    else:
        print(f"radius={Decimal(r_str.strip())} area={format(area, 'g')} (prec={prec})")

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
