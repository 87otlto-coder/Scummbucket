"""Bounded source-only audit of SCUMM v5 COST selector/cel references.

No engine run or pose timing inference. Referenced frames are not proof of
script selection at runtime. Errors remain per-selector diagnostics.
"""


def audit_costume_selectors(costume):
    """Validate declared selectors and referenced cel data without drawing.

    Parses original selector masks, limbs and ranges using the same pointer
    convention as the classic costume decoder. Inspects all non-control
    command positions in each range. Does not try to execute SCUMM scripts.
    """
    data = costume.data
    selectors = []
    unique = set()
    zero_refs = []
    failures = []
    with_ranges = 0
    defined = 0
    for selector in range(data[8] + 1):
        row = {"selector": selector, "status": "unused", "limb_ranges": 0,
               "cel_references": 0, "zero_area_references": 0}
        selectors.append(row)
        limb = None
        position = None
        try:
            table = costume.table_start + 34 + 2 * selector
            if table + 2 > len(data):
                raise ValueError("truncated selector pointer table")
            if data[table:table + 2] == b"\0\0":
                continue
            defined += 1
            p = costume.pointer(table)
            if p + 2 > len(data):
                raise ValueError("truncated selector limb mask")
            mask = int.from_bytes(data[p:p + 2], "little")
            p += 2
            ranges = []
            for limb in range(16):
                if not mask & (0x8000 >> limb):
                    continue
                if p + 2 > len(data):
                    raise ValueError("truncated selector limb position")
                start = int.from_bytes(data[p:p + 2], "little")
                p += 2
                if start == 0xFFFF:
                    continue
                if p >= len(data):
                    raise ValueError("truncated selector limb extent")
                extra = data[p]
                p += 1
                end = start + (extra & 0x7f)
                if costume.commands + end >= len(data):
                    raise ValueError("selector command range outside COST")
                initial = data[costume.commands + start]
                if initial in (0x79, 0x7a):
                    continue  # SCUMM stop/resume state, not a drawable cel.
                ranges.append((limb, start, end))
            row["limb_ranges"] = len(ranges)
            if ranges:
                with_ranges += 1
            for limb, start, end in ranges:
                for position in range(start, end + 1):
                    code = data[costume.commands + position] & 0x7f
                    if code in (0x78, 0x79, 0x7a, 0x7b, 0x7c):
                        continue
                    result = costume.limb(limb, position)
                    if result is None:
                        continue
                    _, cel = result
                    row["cel_references"] += 1
                    unique.add((limb, position))
                    if cel.width == 0 or cel.height == 0:
                        row["zero_area_references"] += 1
                        zero_refs.append({"selector": selector, "limb": limb,
                                          "position": position,
                                          "width": cel.width, "height": cel.height})
            row["status"] = "consistent"
        except (ValueError, IndexError) as exc:
            row["status"] = "failed"
            row["error"] = {"type": type(exc).__name__, "message": str(exc),
                            "limb": limb, "position": position}
            failures.append({"selector": selector, **row["error"]})
    return {
        "declared_selector_slots": len(selectors),
        "defined_pointer_slots": defined,
        "selector_slots_with_ranges": with_ranges,
        "consistent_selector_slots": sum(x["status"] == "consistent" for x in selectors),
        "unused_selector_slots": sum(x["status"] == "unused" for x in selectors),
        "failed_selector_slots": len(failures),
        "cel_references_examined": sum(x["cel_references"] for x in selectors),
        "distinct_limb_position_references": len(unique),
        "zero_area_references": zero_refs,
        "failures": failures,
    }
