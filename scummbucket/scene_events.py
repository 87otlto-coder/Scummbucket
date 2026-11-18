"""Versioned, renderer-neutral P4 event manifests in explicit input order."""

import json
import re

EVIDENCE = frozenset({
    "archive_decoded", "engine_source_backed", "script_static_aligned",
    "runtime_observed", "pixel_verified", "synthetic", "unsupported",
})

# Required payload fields and their types. Additional JSON fields can carry
# conditions, source annotations and engine-specific details.
FIELDS = {
    "object_state": {"object_id": int, "state": int},
    "object_draw": {"object_id": int, "state": int},
    "object_position": {"object_id": int, "x": int, "y": int},
    "object_class": {"object_id": int, "class_id": int, "enabled": bool},
    "palette_cycle": {"cycle_id": int, "first": int, "last": int, "flags": int},
    "palette_phase": {"cycle_id": int, "rotations": int, "counter": int},
    "palette_intensity": {"first": int, "last": int, "red": int, "green": int, "blue": int},
    "actor_costume": {"actor_id": int, "costume_id": int},
    "actor_position": {"actor_id": int, "x": int, "y": int},
    "actor_animation": {"actor_id": int, "animation": int},
    "layer_order": {"layers": list},
    "transparency": {"index": int},
    "zplane": {"plane": int, "enabled": bool},
    "script_start": {"script_id": int},
    "script_stop": {},
    "script_yield": {},
    "conditional_transition": {"condition": str, "taken": (bool, type(None))},
    "room_transition": {"logical_room": int, "physical_room": int},
    "unknown": {"reason": str},
    "unsupported": {"reason": str},
}


class SceneEventError(ValueError):
    """A malformed manifest, with its failing field path."""


def _require(condition, path, explanation):
    if not condition:
        raise SceneEventError(f"{path}: {explanation}")


def _fields(row, expected, path):
    _require(type(row) is dict, path, "expected an object")
    for name, kinds in expected.items():
        allowed = kinds if isinstance(kinds, tuple) else (kinds,)
        _require(name in row and type(row[name]) in allowed, f"{path}.{name}",
                 "expected " + " or ".join(kind.__name__ for kind in allowed))


def _natural(value, path):
    _require(type(value) is int and value >= 0, path, "expected a nonnegative integer")


def _json_value(value, path):
    if type(value) is dict:
        for key, item in value.items():
            _require(type(key) is str, path, "JSON object keys must be strings")
            _json_value(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _json_value(item, f"{path}[{index}]")
    else:
        _require(type(value) in (str, int, bool, type(None)), path,
                 "expected an integer, string, boolean, null, array or object")


def serialize_scene_events(manifest):
    """Validate and emit canonical UTF-8 JSON. Array order is event order.

    A null tick means timing is unknown. Ticks use the caller-declared clock.
    A null script PC means the event is only attributed to a script or resource.
    """
    _fields(manifest, {"schema": str, "source": dict, "clock": (str, type(None)),
                       "events": list}, "manifest")
    _require(manifest["schema"] == "p4-scene-events/1", "schema", "unsupported version")
    source = manifest["source"]
    _fields(source, {"game_edition": str, "archive_sha256": str, "logical_room": int,
                     "physical_room": int}, "source")
    _require(bool(source["game_edition"].strip()), "source.game_edition", "empty edition")
    _require(re.fullmatch("[0-9a-f]{64}", source["archive_sha256"]) is not None,
             "source.archive_sha256", "expected lowercase SHA-256")
    for name in ("logical_room", "physical_room"):
        _natural(source[name], f"source.{name}")
    clock = manifest["clock"]
    _require(clock is None or bool(clock.strip()), "clock", "empty clock name")
    previous_tick = 0
    for index, event in enumerate(manifest["events"]):
        path = f"events[{index}]"
        _fields(event, {"kind": str, "evidence": str, "tick": (int, type(None)),
                        "payload": dict}, path)
        kind = event["kind"]
        _require(kind in FIELDS, f"{path}.kind", "unknown event kind")
        _require(event["evidence"] in EVIDENCE, f"{path}.evidence", "unknown evidence status")
        _require(kind != "unsupported" or event["evidence"] == "unsupported",
                 f"{path}.evidence", "unsupported events require unsupported evidence")
        tick = event["tick"]
        if tick is not None:
            _require(clock is not None and tick >= previous_tick, f"{path}.tick",
                     "requires a declared clock and a nondecreasing nonnegative tick")
            previous_tick = tick
        script = event.get("script")
        if script is not None:
            _fields(script, {"kind": str, "storage_room": (int, type(None)),
                             "id": (int, type(None)), "pc": (int, type(None))},
                    f"{path}.script")
            for name in ("storage_room", "id", "pc"):
                if script[name] is not None:
                    _natural(script[name], f"{path}.script.{name}")
        payload = event["payload"]
        _fields(payload, FIELDS[kind], f"{path}.payload")
        for name in FIELDS[kind]:
            if type(payload[name]) is int and name not in ("x", "y"):
                _natural(payload[name], f"{path}.payload.{name}")
        if "first" in FIELDS[kind]:
            _require(payload["first"] <= payload["last"] <= 255,
                     f"{path}.payload", "invalid palette range")
        if kind in ("unknown", "unsupported"):
            _require(bool(payload["reason"].strip()), f"{path}.payload.reason", "empty reason")
    _json_value(manifest, "manifest")
    return (json.dumps(manifest, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
            + "\n").encode("utf-8")
