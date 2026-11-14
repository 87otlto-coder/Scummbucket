"""Conservative SCUMM v5 object-state *byte-pattern* survey, not a disassembler.

Searches for sequences matching direct-object operands of drawObject/setState.
Scanning is NOT aligned to decoded instruction boundaries: data strings,
immediates, and unreachable code could match. Never treat candidates as proof
of script control, runtime execution, or animation/frame timing.
"""
from __future__ import annotations

from collections import Counter

# ScummVM: script_v5.cpp setupOpcodes()/o5_drawObject()/o5_setState().
# Variants with object operand held directly as a 16-bit literal.
_DRAW_DIRECT = (0x05, 0x45)
_SET_DIRECT = (0x07, 0x47)


def scan_room_script_patterns(decoded: bytes, scenes: list[dict],
                              *, source: str) -> tuple[dict, list[dict]]:
    """Annotate each scene with possible object state operations and provenance."""
    diagnostics: list[dict] = []
    totals = Counter()
    rooms_with_patterns = 0

    for room in scenes:
        rid = room["room_id"]
        object_ids = {o["object_id"] for o in room["objects"]}
        room_hits: list[dict] = []

        for script in room["local_script_chunks"]:
            tag, offset, length = script["tag"], script["source_offset"], script["byte_length"]
            header_size = 9 if tag == "LSCR" else 8
            if offset < 0 or length < header_size or offset + length > len(decoded):
                diagnostics.append({
                    "severity": "error", "code": "SCRIPT_CHUNK_RANGE_INVALID",
                    "message": f"Room {rid}: invalid {tag} script source range",
                    "source": source, "offset": offset, "tag": tag, "resource_id": rid})
                continue

            script_id = decoded[offset + 8] if tag == "LSCR" else None
            body_offset = offset + header_size
            body = decoded[body_offset:offset + length]
            # This byte-wise search is intentionally NOT a full opcode decoder.
            # Every returned match carries an explicit unverified-alignment flag.
            for n in range(max(0, len(body) - 2)):
                opcode = body[n]
                if opcode not in _DRAW_DIRECT and opcode not in _SET_DIRECT:
                    continue
                object_id = int.from_bytes(body[n + 1:n + 3], "little")
                if object_id not in object_ids:
                    continue

                if opcode in _DRAW_DIRECT:
                    if n + 4 > len(body):
                        diagnostics.append({
                            "severity": "warning", "code": "SCRIPT_PATTERN_INCOMPLETE",
                            "message": "Potential drawObject instruction ends at script boundary",
                            "source": source, "offset": body_offset + n, "tag": tag,
                            "resource_id": object_id})
                        continue
                    subopcode = body[n + 3]
                    # Only SO_DRAW_STATE (subopcode 2) is in scope.
                    if subopcode & 0x1F != 2:
                        continue
                    if n + 6 > len(body):
                        diagnostics.append({
                            "severity": "warning", "code": "SCRIPT_PATTERN_INCOMPLETE",
                            "message": "Potential drawObject state argument is incomplete",
                            "source": source, "offset": body_offset + n, "tag": tag,
                            "resource_id": object_id})
                        continue
                    state_operand = int.from_bytes(body[n + 4:n + 6], "little")
                    state_mode = "variable_reference" if subopcode & 0x80 else "literal"
                    used = 6
                    operation = "drawObject"
                else:
                    state_mode = "variable_reference" if opcode & 0x40 else "literal"
                    used = 5 if state_mode == "variable_reference" else 4
                    if n + used > len(body):
                        diagnostics.append({
                            "severity": "warning", "code": "SCRIPT_PATTERN_INCOMPLETE",
                            "message": "Potential setState argument is incomplete",
                            "source": source, "offset": body_offset + n, "tag": tag,
                            "resource_id": object_id})
                        continue
                    state_operand = (int.from_bytes(body[n + 3:n + 5], "little")
                                     if state_mode == "variable_reference" else body[n + 3])
                    subopcode = None
                    operation = "setState"

                candidate = {
                    "room_id": rid, "object_id": object_id,
                    "script_tag": tag, "script_id": script_id,
                    "script_chunk_offset": offset,
                    "source_offset": body_offset + n, "script_body_offset": n,
                    "opcode_hex": f"0x{opcode:02X}",
                    "operation_candidate": operation,
                    "state_operand_mode": state_mode,
                    "state_operand_raw": state_operand,
                    "raw_pattern_hex": body[n:n + used].hex(),
                    "evidence": "raw_pattern_matches_scumm_v5_operand_layout",
                    "instruction_alignment_verified": False,
                    "runtime_execution_verified": False,
                    "script_control_verified": False,
                }
                if subopcode is not None:
                    candidate["subopcode_hex"] = f"0x{subopcode:02X}"
                room_hits.append(candidate)
                totals["all_patterns"] += 1
                totals[operation] += 1

        room["script_state_candidates"] = room_hits
        if room_hits:
            rooms_with_patterns += 1
        by_object = Counter(hit["object_id"] for hit in room_hits)
        for obj in room["objects"]:
            obj["script_state_pattern_count"] = by_object[obj["object_id"]]
            # A pattern does not upgrade an animation or control assertion.
            obj["script_control_verified"] = False

    summary = {
        "all_patterns": totals["all_patterns"],
        "drawObject_patterns": totals["drawObject"],
        "setState_patterns": totals["setState"],
        "rooms_with_patterns": rooms_with_patterns,
        "instruction_alignment_verified": False,
    }
    return summary, diagnostics
