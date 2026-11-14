"""Resolve SCUMM v5 index resource IDs into validated room-bundle chunks.

This is structural linking, not script interpretation, asset decoding, or proof
that any particular object or costume animates during gameplay.
"""
from __future__ import annotations

from collections import Counter

# ScummVM: resource.cpp readResTypeList(), loadResource(),
# getResourceRoomNr(), getResourceRoomOffset(), and readRoomsOffsets().
TYPE_TAGS = {
    "DROO": "ROOM",
    "DSCR": "SCRP",
    "DSOU": "SOUN",
    "DCOS": "COST",
    "DCHR": "CHAR",
}


def link_index_resources(index: dict, resources: dict, *, source: str | None = None) -> tuple[dict, list[dict]]:
    """Map directory resource slots to verified chunk boundaries.

    Returned entries have status 'linked', 'unused', or 'failed'. A populated
    entry is 'linked' only if its calculated source offset matches a parsed
    direct ROOM/LFLF child of the expected tag in the correct room.
    No external game bytes are read or modified.
    """
    rooms = {r["id"]: r for r in resources["rooms"]}
    positions: dict[tuple[int, int], dict] = {}
    diagnostics: list[dict] = []
    for item in resources["resource_inventory"]:
        key = (item["room_id"], item["offset"])
        if key in positions:
            diagnostics.append({"severity": "error", "code": "INVENTORY_LOCATION_DUPLICATE",
                                "message": f"Repeated room {key[0]} resource at 0x{key[1]:X}",
                                "source": source, "offset": key[1], "tag": item["tag"],
                                "resource_id": key[0]})
        else:
            positions[key] = item

    entries: list[dict] = []
    counts: dict[str, dict[str, int]] = {}
    all_offsets: dict[int, tuple[str, int]] = {}

    for directory, expected_tag in TYPE_TAGS.items():
        table = index.get(directory)
        if not table:
            diagnostics.append({"severity": "error", "code": "DIRECTORY_MISSING",
                                "message": f"Missing directory {directory}",
                                "source": source, "offset": None, "tag": directory, "resource_id": None})
            continue
        local_counts: Counter = Counter()
        records = table.get("resource_locations", [])
        if len(records) != table.get("slots"):
            diagnostics.append({"severity": "error", "code": "DIRECTORY_SLOTS_INCONSISTENT",
                                "message": f"{directory} reports {table.get('slots')} slots but has {len(records)} records",
                                "source": source, "offset": None, "tag": directory, "resource_id": None})
        for record in records:
            resource_id, room_number, room_offset = record["id"], record["room_number"], record["offset"]
            entry = {"directory": directory, "id": resource_id, "room_number_raw": room_number,
                     "room_relative_offset": room_offset, "room_id": None, "expected_tag": expected_tag,
                     "source_offset": None, "byte_length": None, "status": "failed"}
            entries.append(entry)

            if room_number == 0 and room_offset == 0:
                entry["status"] = "unused"
                local_counts["unused"] += 1
                continue

            # DOS v5 case: DROO 'room_number' identifies the container file
            # (MONKEY2.001). Room identity comes from the index slot, and
            # the ROOM absolute position is obtained from LOFF.
            if directory == "DROO":
                room_id = resource_id
                if room_number != 1 or room_offset != 0:
                    code = "ROOM_DIRECTORY_UNSUPPORTED"
                    message = (f"Room slot {resource_id}: expected file no. 1 and offset 0, "
                               f"got file no. {room_number} and offset {room_offset}")
                else:
                    code = message = None
            else:
                room_id = room_number
                code = message = None
            entry["room_id"] = room_id
            room = rooms.get(room_id)
            if code is None and room is None:
                code = "DIRECTORY_ROOM_UNRESOLVED"
                message = f"{directory}[{resource_id}] refers to unknown room {room_id}"

            if code is None:
                source_offset = room["room_offset"] + room_offset
                entry["source_offset"] = source_offset
                if directory == "DROO":
                    actual_tag = "ROOM"
                    actual_length = room["room_size"]
                else:
                    actual = positions.get((room_id, source_offset))
                    actual_tag = actual["tag"] if actual else None
                    actual_length = actual["length"] if actual else None
                if actual_tag is None:
                    code = "DIRECTORY_TARGET_MISSING"
                    message = (f"{directory}[{resource_id}] points to 0x{source_offset:X}; "
                               f"no chunk starts there in room {room_id}")
                elif actual_tag != expected_tag:
                    code = "DIRECTORY_TAG_MISMATCH"
                    message = (f"{directory}[{resource_id}] expected {expected_tag}, "
                               f"found {actual_tag} at 0x{source_offset:X}")
                else:
                    entry["byte_length"] = actual_length
                    entry["status"] = "linked"
                    local_counts["linked"] += 1
                    if source_offset in all_offsets:
                        other_type, other_id = all_offsets[source_offset]
                        diagnostics.append({"severity": "warning", "code": "DIRECTORY_TARGET_REUSED",
                                            "message": (f"{directory}[{resource_id}] shares offset "
                                                        f"0x{source_offset:X} with {other_type}[{other_id}]"),
                                            "source": source, "offset": source_offset,
                                            "tag": expected_tag, "resource_id": resource_id})
                    all_offsets[source_offset] = (directory, resource_id)
                    continue

            entry["status"] = "failed"
            local_counts["failed"] += 1
            diagnostics.append({"severity": "error", "code": code, "message": message,
                                "source": source, "offset": entry["source_offset"],
                                "tag": expected_tag, "resource_id": resource_id})
        counts[directory] = {status: local_counts[status] for status in ("linked", "unused", "failed")}

    totals = {status: sum(c[status] for c in counts.values()) for status in ("linked", "unused", "failed")}
    return {"entries": entries, "by_directory": counts, "summary": totals}, diagnostics
