"""Conservative scene relationship inventory for original DOS SCUMM v5.

Only object IDs recorded in IMHD/CDHD are *linked*. Scripts, palettes, and
costumes stored in the same room container are contextual, not proven
references or evidence of animation playback. No scripts are interpreted.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .inspector import InspectionError, chunks


def _diagnostic(code: str, message: str, *, source: str, offset: int | None,
                tag: str | None, resource_id: int | None,
                severity: str = "error") -> dict:
    return {"severity": severity, "code": code, "message": message,
            "source": source, "offset": offset, "tag": tag, "resource_id": resource_id}


def _object_header(decoded: bytes, item: dict, source: str) -> tuple[dict | None, list[dict]]:
    """Parse only the small, well-established v5 IMHD/CDHD header fields."""
    tag = item["tag"]
    offset = item["offset"]
    room_id = item["room_id"]
    header_tag = "IMHD" if tag == "OBIM" else "CDHD"
    diags: list[dict] = []
    try:
        children = chunks(decoded, offset + 8, offset + item["length"], source)
    except InspectionError as exc:
        diags.append(_diagnostic("OBJECT_CHILD_STRUCTURE_INVALID",
                                 f"{tag} nested data cannot be read: {exc}",
                                 source=source, offset=offset, tag=tag, resource_id=room_id))
        return None, diags

    headers = [c for c in children if c.tag == header_tag]
    if len(headers) != 1:
        diags.append(_diagnostic("OBJECT_HEADER_COUNT_INVALID",
                                 f"{tag} must have one {header_tag}; found {len(headers)}",
                                 source=source, offset=offset, tag=tag, resource_id=room_id))
        return None, diags

    h = headers[0]
    min_len = 12 if header_tag == "IMHD" else 10
    if h.length < min_len:
        diags.append(_diagnostic("OBJECT_HEADER_TRUNCATED",
                                 f"{header_tag} is too short for object ID and declared state count",
                                 source=source, offset=h.offset, tag=header_tag, resource_id=room_id))
        return None, diags

    obj_id = int.from_bytes(decoded[h.offset + 8:h.offset + 10], "little")
    record = {"object_id": obj_id, "chunk_tag": tag, "source_offset": offset,
              "byte_length": item["length"], "header_offset": h.offset,
              "evidence": "decoded_v5_header"}

    if tag == "OBIM":
        declared = int.from_bytes(decoded[h.offset + 10:h.offset + 12], "little")
        states = [c.tag for c in children if c.tag.startswith("IM")
                  and len(c.tag) == 4 and c.tag[2] in "0123456789ABCDEF"
                  and c.tag[3] in "0123456789ABCDEF"]
        record["declared_image_count"] = declared
        record["image_state_tags"] = states
        record["observed_image_count"] = len(states)
        if declared != len(states):
            diags.append(_diagnostic("OBJECT_IMAGE_COUNT_MISMATCH",
                                     f"Object {obj_id}: IMHD declares {declared} images, "
                                     f"but {len(states)} IMxx chunks were found",
                                     source=source, offset=h.offset, tag=header_tag,
                                     resource_id=obj_id, severity="warning"))
    return record, diags


def build_scene_inventory(decoded: bytes, resources: dict, directory_links: dict,
                          *, source: str) -> tuple[dict, list[dict]]:
    """Create observed relationships and clearly labeled animation *candidates*.

    The original input stays unchanged and no extracted game bytes are returned.
    Fatal object-local format problems stay visible as per-object diagnostics.
    """
    resource_by_room = defaultdict(list)
    for item in resources["resource_inventory"]:
        resource_by_room[item["room_id"]].append(item)
    global_refs = defaultdict(lambda: {"scripts": [], "costumes": []})
    for entry in directory_links.get("entries", []):
        if entry["status"] != "linked":
            continue
        if entry["directory"] in ("DSCR", "DCOS"):
            bucket = "scripts" if entry["directory"] == "DSCR" else "costumes"
            global_refs[entry["room_id"]][bucket].append(
                {"id": entry["id"], "source_offset": entry["source_offset"],
                 "byte_length": entry["byte_length"],
                 "relationship": "stored_in_room_bundle_only"})

    diagnostics: list[dict] = []
    scenes: list[dict] = []
    totals = Counter()
    for room in sorted(resources["rooms"], key=lambda r: r["id"]):
        rid = room["id"]
        imgs = defaultdict(list)
        codes = defaultdict(list)
        items = resource_by_room[rid]
        for item in items:
            if item["tag"] not in ("OBIM", "OBCD"):
                continue
            record, record_diags = _object_header(decoded, item, source)
            diagnostics.extend(record_diags)
            totals["object_chunks_seen"] += 1
            if record is None:
                totals["unreadable_object_chunks"] += 1
                continue
            (imgs if item["tag"] == "OBIM" else codes)[record["object_id"]].append(record)

        pairs = []
        for object_id in sorted(set(imgs) | set(codes)):
            images, metadata = imgs[object_id], codes[object_id]
            linked = len(images) == len(metadata) == 1
            if len(images) > 1 or len(metadata) > 1:
                diagnostics.append(_diagnostic(
                    "OBJECT_ID_AMBIGUOUS",
                    f"Room {rid} object {object_id}: {len(images)} OBIM and {len(metadata)} OBCD chunks",
                    source=source, offset=(images or metadata)[0]["source_offset"],
                    tag=None, resource_id=object_id))
                totals["ambiguous_objects"] += 1
            elif not linked:
                diagnostics.append(_diagnostic(
                    "OBJECT_COUNTERPART_MISSING",
                    f"Room {rid} object {object_id}: {len(images)} OBIM and {len(metadata)} OBCD chunks",
                    source=source, offset=(images or metadata)[0]["source_offset"],
                    tag=None, resource_id=object_id, severity="warning"))
                totals["unpaired_objects"] += 1
            else:
                totals["paired_objects"] += 1

            image = images[0] if len(images) == 1 else None
            code = metadata[0] if len(metadata) == 1 else None
            candidate = bool(linked and image is not None and image["observed_image_count"] >= 2)
            if candidate:
                totals["multistate_object_candidates"] += 1
            pairs.append({"object_id": object_id, "status": "paired" if linked else
                          "ambiguous" if len(images) > 1 or len(metadata) > 1 else "unpaired",
                          "image": image, "code": code,
                          "background_animation_candidate": candidate,
                          "candidate_reason": "multiple_stored_image_states" if candidate else None,
                          "animation_observed": False,
                          "script_control_verified": False})

        local = [{"tag": item["tag"], "source_offset": item["offset"],
                  "byte_length": item["length"], "relationship": "present_in_room"}
                 for item in items if item["tag"] in ("LSCR", "ENCD", "EXCD")]
        cycles = room["palette_cycles"]
        if cycles:
            totals["rooms_with_palette_cycle_candidates"] += 1
        if any(p["background_animation_candidate"] for p in pairs):
            totals["rooms_with_multistate_candidates"] += 1
        totals["palette_cycle_records"] += len(cycles)
        scenes.append({
            "room_id": rid, "room_offset": room["room_offset"],
            "room_size": room["room_size"], "objects": pairs,
            "palette_cycles": cycles, "local_script_chunks": local,
            "global_scripts_stored_here": sorted(global_refs[rid]["scripts"], key=lambda x: x["id"]),
            "costumes_stored_here": sorted(global_refs[rid]["costumes"], key=lambda x: x["id"]),
            "evidence": {"object_pairs": "header_id_match",
                         "palette_cycles": "directly_parsed_records",
                         "scripts_and_costumes": "storage_association_only",
                         "animation_playback": "not_verified"}
        })
    summary = {key: totals[key] for key in (
        "paired_objects", "unpaired_objects", "ambiguous_objects",
        "unreadable_object_chunks", "object_chunks_seen",
        "multistate_object_candidates", "rooms_with_multistate_candidates",
        "palette_cycle_records", "rooms_with_palette_cycle_candidates")}
    summary["rooms"] = len(scenes)
    return {"summary": summary, "rooms": scenes, "status": "structural_relationships_only"}, diagnostics
