#!/usr/bin/env python3
"""
Run tests for circle-area-tool scripts.
Print a JSON summary with per-case details.
"""
from __future__ import annotations
import json
from decimal import Decimal, getcontext, InvalidOperation
from pathlib import Path
import sys

# Ensure we can import circle_area.py from the same directory
THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

try:
    import circle_area
except Exception as e:
    print(json.dumps({"ok": False, "error": f"failed to import circle_area: {e}"}))
    raise SystemExit(1)


def approx_equal(a: Decimal, b: Decimal, sig_digits: int) -> bool:
    """Compare two Decimal numbers to given significant digits by rounding both to that precision."""
    local = getcontext().copy()
    local.prec = sig_digits
    with local:
        return +a == +b


def run() -> int:
    results = []

    # Choose a working precision for tests
    P = 50

    # Valid cases: (input, description)
    valids = [
        ("0", "zero radius"),
        ("1", "unit radius"),
        ("2.5", "decimal radius"),
        ("1e100", "very large radius"),
        ("1e-100", "very small radius"),
        (" 7 ", "whitespace"),
        ("3.1415926535", "pi-like radius"),
        ("2.220446049250313e-16", "tiny float epsilon-ish"),
    ]

    for r_str, note in valids:
        try:
            area, _ = circle_area.compute_area(r_str, precision=P)
            # Expected using same high-precision pi constant and Decimal
            ctx = getcontext().copy(); ctx.prec = P + 15
            with ctx:
                r = ctx.create_decimal(r_str.strip())
                expected = (r * r) * circle_area._PI_DEC
            ok = approx_equal(area, expected, sig_digits=P)
            results.append({"case": f"valid: {note}", "radius": r_str, "ok": ok, "area": format(area, 'g')})
        except Exception as e:
            results.append({"case": f"valid: {note}", "radius": r_str, "ok": False, "error": str(e)})

    # Invalid cases: should raise ValueError
    invalids = [
        ("-1", "negative"),
        ("nan", "NaN"),
        ("inf", "Infinity"),
        ("-inf", "-Infinity"),
        ("abc", "non-numeric"),
    ]

    for r_str, note in invalids:
        try:
            _ = circle_area.compute_area(r_str, precision=P)
            results.append({"case": f"invalid: {note}", "radius": r_str, "ok": False, "error": "expected failure but succeeded"})
        except ValueError:
            results.append({"case": f"invalid: {note}", "radius": r_str, "ok": True})
        except Exception as e:
            results.append({"case": f"invalid: {note}", "radius": r_str, "ok": False, "error": str(e)})

    summary_ok = all(item.get("ok", False) for item in results if item["case"].startswith("valid")) \
                 and all(item.get("ok", False) for item in results if item["case"].startswith("invalid"))

    print(json.dumps({"ok": summary_ok, "results": results}, indent=2))
    return 0 if summary_ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
