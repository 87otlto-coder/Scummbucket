"""Compare paired native indexed rasters and 256-entry RGB palettes."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def _compare(actual, reference, *, size, unit, locate):
    if len(actual) != size or len(reference) != size:
        raise ValueError(f"Expected {size} bytes in each buffer, got {len(actual)} and {len(reference)}")
    count = 0
    first = None
    for offset in range(0, size, unit):
        got = actual[offset:offset + unit]
        expected = reference[offset:offset + unit]
        if got != expected:
            count += 1
            if first is None:
                first = dict(location=locate(offset // unit), actual=list(got),
                             expected=list(expected))
    return dict(compared=size // unit, mismatches=count, first_mismatch=first,
                actual_sha256=sha256(actual).hexdigest(),
                reference_sha256=sha256(reference).hexdigest())


def compare_native_frame(actual_indices, actual_palette, reference_indices, reference_palette,
                         *, width, height):
    """Report indexed pixel and RGB entry mismatches independently."""
    if not 0 < width <= 2048 or not 0 < height <= 1024:
        raise ValueError("Unsupported native frame geometry")
    return dict(
        width=width, height=height,
        indices=_compare(actual_indices, reference_indices, size=width * height, unit=1,
                         locate=lambda offset: dict(x=offset % width, y=offset // width)),
        palette=_compare(actual_palette, reference_palette, size=768, unit=3,
                         locate=lambda index: dict(index=index)),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual_indices", type=Path)
    parser.add_argument("actual_palette", type=Path)
    parser.add_argument("reference_indices", type=Path)
    parser.add_argument("reference_palette", type=Path)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    args = parser.parse_args()
    paths = (args.actual_indices, args.actual_palette, args.reference_indices, args.reference_palette)
    try:
        report = compare_native_frame(*(path.read_bytes() for path in paths),
                                      width=args.width, height=args.height)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True, indent=2))
    return int(bool(report["indices"]["mismatches"] or report["palette"]["mismatches"]))


if __name__ == "__main__":
    raise SystemExit(main())
