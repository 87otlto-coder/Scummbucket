"""Read-only MI2 DOS VGA COST inventory, including all selector failures.

  python -B -m tools.audit_costume_corpus --game ORIGINAL_MI2_DIR_OR_ZIP \
    --output NEW_REPORT.json

Original files are read twice and source fingerprints revalidated. Output
contains only metadata, counts and diagnostics; no game pixels or COST bytes.
Only a NEW, explicitly supplied report path can be written. Without --output,
the JSON report is printed to stdout. Partial results exit with status 2.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.classic_costume import ClassicCostume
from scummbucket.costume_corpus import audit_costume_selectors
from scummbucket.inspector import XOR_KEY, _read_pair, inspect


COUNTS = ("declared_selector_slots", "defined_pointer_slots",
          "selector_slots_with_ranges", "consistent_selector_slots",
          "unused_selector_slots", "failed_selector_slots",
          "cel_references_examined", "distinct_limb_position_references",
          "distinct_failed_reference_groups")


def audit(game):
    source = Path(game)
    report = {
        "schema": "scummbucket-costume-corpus/1",
        "status": "failed",
        "input": str(source),
        "evidence": "original_archive_decoding_not_runtime",
        "runtime_selection_verified": False,
        "runtime_fidelity_verified": False,
        "source_hashes": [],
        "summary": {"linked_costumes": 0, "unused_costume_slots": 0,
                    "failed_costumes": 0, "costumes_16_color": 0,
                    "costumes_32_color": 0, **{key: 0 for key in COUNTS}},
        "costumes": [], "diagnostics": [],
    }

    def issue(code, message, **location):
        report["diagnostics"].append({"code": code, "message": str(message), **location})

    try:
        inventory = inspect(source)
        if inventory["status"] != "success":
            raise ValueError("Archive inspection not successful; inspect its diagnostics separately")
        index, raw, index_label, resource_label = _read_pair(source)
        fingerprints = [sha256(index).hexdigest(), sha256(raw).hexdigest()]
        if fingerprints != [r["sha256"] for r in inventory["sources"]]:
            raise ValueError("Original game bytes changed between inventory and reopen")
        report["source_hashes"] = [
            {"name": name.rsplit("/", 1)[-1], "size": len(content),
             "sha256": digest}
            for name, content, digest in
            zip((index_label, resource_label), (index, raw), fingerprints)
        ]
        data = bytes(b ^ XOR_KEY for b in raw)
        records = [r for r in inventory["directory_links"]["entries"]
                   if r["directory"] == "DCOS"]
        if not records:
            raise ValueError("Original index has no DCOS entries")
    except (OSError, ValueError, KeyError, IndexError) as exc:
        issue("SOURCE_PREFLIGHT_FAILED", exc)
        return report

    totals = report["summary"]
    for item in records:
        cost_id = item["id"]
        status = item["status"]
        if status == "unused":
            totals["unused_costume_slots"] += 1
            continue
        if status != "linked":
            totals["failed_costumes"] += 1
            issue("COST_LINK_FAILED", "Costume directory record not linked",
                  costume_id=cost_id, directory_status=status)
            continue
        row = {"costume_id": cost_id, "room_id": item["room_id"],
               "source_offset": item["source_offset"],
               "source_length": item["byte_length"], "status": "failed"}
        report["costumes"].append(row)
        try:
            off, size = item["source_offset"], item["byte_length"]
            if (type(off) is not int or type(size) is not int or
                    size < 44 or off < 0 or off + size > len(data) or
                    data[off:off + 4] != b"COST" or
                    int.from_bytes(data[off + 4:off + 8], "big") != size):
                raise ValueError("Linked source COST chunk out of bounds or mismatched")
            source_cost = data[off:off + size]
            costume = ClassicCostume(source_cost)
            detail = audit_costume_selectors(costume)
            row.update(status="consistent" if not detail["failures"] else "partial",
                       source_sha256=sha256(source_cost).hexdigest(),
                       colors=costume.colors, **detail)
            totals["linked_costumes"] += 1
            totals[f"costumes_{costume.colors}_color"] += 1
            for key in COUNTS:
                totals[key] += detail[key]
            for failure in detail["failures"]:
                issue("SELECTOR_CEL_FAILED", failure["message"],
                      costume_id=cost_id, room_id=item["room_id"],
                      selector=failure["selector"], limb=failure["limb"],
                      position=failure["position"])
            if detail["failures"]:
                totals["failed_costumes"] += 1
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            totals["failed_costumes"] += 1
            row["failure"] = f"{type(exc).__name__}: {exc}"
            issue("COST_SOURCE_FAILED", row["failure"], costume_id=cost_id,
                  room_id=item["room_id"])
    if totals["linked_costumes"]:
        report["status"] = "partial" if report["diagnostics"] else "success"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="New non-existing report path (never overwrite)")
    args = parser.parse_args()
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("Output already exists; refusing overwrite")
    report = audit(args.game)
    text = json.dumps(report, indent=2) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(text)
        print(f"Costume audit: {report['status']}; report={args.output}")
        print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
