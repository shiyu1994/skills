#!/usr/bin/env python3
import argparse
import math
import sys
import json


def main():
    parser = argparse.ArgumentParser(description="Compute area of a circle given radius.")
    parser.add_argument("radius", help="Radius of the circle (non-negative real number).", type=float)
    parser.add_argument("--precision", "-p", type=int, default=None, help="Round result to N decimal places.")
    parser.add_argument("--json", action="store_true", help="Output as JSON with fields radius and area.")
    args = parser.parse_args()

    r = args.radius
    if r < 0:
        print("Error: radius must be non-negative.", file=sys.stderr)
        sys.exit(1)

    area = math.pi * r * r

    area_out = round(area, args.precision) if args.precision is not None else area

    if args.json:
        print(json.dumps({"radius": r, "area": area_out}, ensure_ascii=False))
    else:
        print(f"{area_out}")


if __name__ == "__main__":
    main()
