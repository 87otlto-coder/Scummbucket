"""P4 explicit-event native-indexed scene composition, not SCUMM execution.

Each frame supplies its exact ordered draw list. Persistent object selection and
palette changes are applied only when explicit events say so; no camera, actor,
object, script or palette timing is inferred. Scene fidelity is NOT VALIDATED.
"""
from __future__ import annotations

from hashlib import sha256

from .native_object_state import compose_indexed_object


class SceneEventError(ValueError):
    def __init__(self, code: str, message: str, *, event_index: int | None = None):
        super().__init__(message)
        self.code = code
        self.event_index = event_index


def _require(ok, code, message, event_index=None):
    if not ok:
        raise SceneEventError(code, message, event_index=event_index)


def _crop(buffer, room_width, left, top, width, height):
    return b"".join(buffer[(top + y) * room_width + left:
                           (top + y) * room_width + left + width]
                    for y in range(height))


def render_scene_event_frames(scene: dict, object_states: dict, costumes: dict,
                              events: list[dict], *, viewport=None):
    """Yield source-indexed viewport frames for explicitly ordered state events.

    Event kinds: palette_patch, object_state, object_hide, frame.
    Every event requires an integer tick/order and a declared evidence category
    (engine_observed, inferred, manual, synthetic); ordering must be strictly
    increasing by (tick, order). frame.draw_order is mandatory. Object
    state selection does NOT automatically draw the object: each frame lists
    every actual layer explicitly, including recorded actor rows.

    Palette patches edit CLUT entries only. Native image index bytes never
    change in response to a palette patch. Mask planes are optional *room*
    masks selected explicitly by a draw operation; embedded object ZPxx masks
    are not silently interpreted. Actor rows are consumed by the existing
    COST compositor, preserving recorded order and its 255-palette fallback.
    """
    _require(isinstance(scene, dict) and isinstance(scene.get("manifest"), dict),
             "SCENE_INVALID", "Scene with dimensions required")
    dims = scene["manifest"].get("dimensions")
    _require(isinstance(dims, (list, tuple)) and len(dims) == 2 and
             all(type(v) is int for v in dims) and 0 < dims[0] <= 2048 and
             0 < dims[1] <= 1024 and dims[0] * dims[1] <= 2_000_000,
             "SCENE_DIMENSIONS_INVALID", "Invalid source scene dimensions")
    room_w, room_h = dims
    background = scene.get("background")
    palette = scene.get("palette")
    masks = scene.get("masks")
    _require(isinstance(background, bytes) and len(background) == room_w * room_h,
             "SCENE_BACKGROUND_INVALID", "Native source background required")
    _require(isinstance(palette, bytes) and len(palette) == 768,
             "SCENE_PALETTE_INVALID", "Source palette must contain 256 RGB entries")
    _require(isinstance(masks, dict) and isinstance(object_states, dict) and
             isinstance(costumes, dict), "SCENE_RESOURCES_INVALID",
             "Mask, object and costume inventories must be mappings")
    for plane, mask in masks.items():
        _require(type(plane) is int and 1 <= plane <= 255 and
                 isinstance(mask, bytes) and len(mask) == room_w * room_h and
                 all(p in (0, 255) for p in mask), "SCENE_MASK_INVALID",
                 f"Invalid room mask plane {plane!r}")
    if viewport is None:
        viewport = (0, 0, room_w, room_h)
    _require(isinstance(viewport, tuple) and len(viewport) == 4 and
             all(type(v) is int for v in viewport), "VIEWPORT_INVALID",
             "Viewport must be (left, top, width, height)")
    left, top, width, height = viewport
    _require(0 <= left < room_w and 0 <= top < room_h and
             width > 0 and height > 0 and left + width <= room_w and
             top + height <= room_h, "VIEWPORT_INVALID",
             "Viewport must be inside the original scene")
    _require(isinstance(events, list) and len(events) <= 100_000,
             "EVENT_LIST_INVALID", "Bounded ordered event list required")
    base = _crop(background, room_w, left, top, width, height)
    clipped_masks = {p: _crop(mask, room_w, left, top, width, height)
                     for p, mask in masks.items()}
    active = {}
    current_palette = bytearray(palette)
    seen_evidence = set(["archive_decoded"])
    previous = (-1, -1)
    total_pixels = 0
    for i, event in enumerate(events):
        _require(isinstance(event, dict), "EVENT_INVALID", "Expected event mapping", i)
        tick, order, kind, evidence = (event.get(k) for k in
                                      ("tick", "order", "kind", "evidence"))
        _require(type(tick) is int and tick >= 0 and type(order) is int and
                 order >= 0 and (tick, order) > previous,
                 "EVENT_ORDER_INVALID", "Events must have increasing tick/order", i)
        _require(evidence in ("engine_observed", "inferred", "manual", "synthetic"),
                 "EVENT_EVIDENCE_INVALID", "Declare the origin of every event", i)
        previous = (tick, order)
        seen_evidence.add(evidence)
        if kind == "palette_patch":
            _require(set(event) == {"tick", "order", "kind", "evidence", "entries"},
                     "PALETTE_EVENT_INVALID", "Unexpected or missing palette fields", i)
            entries = event["entries"]
            _require(isinstance(entries, list) and 1 <= len(entries) <= 256,
                     "PALETTE_PATCH_INVALID", "Need 1 to 256 explicit CLUT patches", i)
            indexes = set()
            for patch in entries:
                _require(isinstance(patch, dict) and set(patch) == {"index", "rgb"},
                         "PALETTE_PATCH_INVALID", "Invalid CLUT entry", i)
                idx, rgb = patch["index"], patch["rgb"]
                _require(type(idx) is int and 0 <= idx <= 255 and idx not in indexes and
                         isinstance(rgb, (list, tuple)) and len(rgb) == 3 and
                         all(type(v) is int and 0 <= v <= 255 for v in rgb),
                         "PALETTE_PATCH_INVALID", "Invalid or duplicate CLUT index", i)
                indexes.add(idx)
                current_palette[3 * idx:3 * idx + 3] = bytes(rgb)
        elif kind == "object_state":
            _require(set(event) == {"tick", "order", "kind", "evidence",
                                    "object_id", "state_tag", "x", "y"},
                     "OBJECT_EVENT_INVALID", "Unexpected or missing object fields", i)
            obj, tag = event["object_id"], event["state_tag"]
            _require(type(obj) is int and obj > 0 and isinstance(tag, str) and
                     len(tag) == 4 and tag[:2] == "IM" and
                     all(c in "0123456789ABCDEF" for c in tag[2:]),
                     "OBJECT_SELECTION_INVALID", "Object ID and IMxx required", i)
            state = object_states.get((obj, tag))
            _require(isinstance(state, dict) and state.get("object_id") == obj and
                     state.get("state_tag") == tag,
                     "OBJECT_STATE_MISSING", "No matching source-decoded object state", i)
            x, y = event["x"], event["y"]
            _require(type(x) is int and type(y) is int and
                     -100_000 <= x <= 100_000 and -100_000 <= y <= 100_000,
                     "OBJECT_POSITION_INVALID", "Explicit room object origin required", i)
            active[obj] = (state, x, y)
        elif kind == "object_hide":
            _require(set(event) == {"tick", "order", "kind", "evidence", "object_id"},
                     "OBJECT_EVENT_INVALID", "Unexpected or missing hide fields", i)
            obj = event["object_id"]
            _require(type(obj) is int and obj in active, "OBJECT_NOT_ACTIVE",
                     "Cannot hide an unselected object", i)
            del active[obj]
        elif kind == "frame":
            _require(set(event) == {"tick", "order", "kind", "evidence", "draw_order"},
                     "FRAME_EVENT_INVALID", "Explicit draw_order is required", i)
            draws = event["draw_order"]
            _require(isinstance(draws, list) and len(draws) <= 256,
                     "FRAME_DRAW_ORDER_INVALID", "Bounded ordered draw list required", i)
            total_pixels += width * height
            _require(total_pixels <= 50_000_000, "FRAME_BUDGET_EXCEEDED",
                     "Total generated viewport pixels exceed safe limit", i)
            canvas = bytes(base)
            for j, draw in enumerate(draws):
                _require(isinstance(draw, dict) and "kind" in draw,
                         "DRAW_INVALID", f"Invalid draw operation {j}", i)
                if draw["kind"] == "object":
                    _require(set(draw) == {"kind", "object_id", "occlusion_plane"},
                             "DRAW_INVALID", "Explicit object ID and room plane required", i)
                    obj, plane = draw["object_id"], draw["occlusion_plane"]
                    _require(type(obj) is int and obj in active,
                             "OBJECT_NOT_ACTIVE", f"Draw uses unknown/hidden object {obj!r}", i)
                    _require(type(plane) is int and (plane == 0 or plane in clipped_masks),
                             "OCCLUSION_PLANE_MISSING", "Unrecorded/missing room plane", i)
                    state, x, y = active[obj]
                    try:
                        canvas = compose_indexed_object(
                            canvas, width, height, state, x=x-left, y=y-top,
                            occlusion=clipped_masks.get(plane))
                    except ValueError as exc:
                        raise SceneEventError(
                            "OBJECT_COMPOSITION_FAILED",
                            f"Draw {j}: source object {obj}: {exc}",
                            event_index=i) from exc
                elif draw["kind"] == "actor":
                    _require(set(draw) == {"kind", "row"} and isinstance(draw["row"], dict),
                             "DRAW_INVALID", "Actor requires a recorded draw-phase row", i)
                    from .scene_source import compose_actor_layers
                    view = {"manifest": {"dimensions": [width, height]},
                            "background": canvas, "masks": clipped_masks}
                    try:
                        canvas = compose_actor_layers(view, costumes, [draw["row"]],
                                                      viewport=(0, 0, width, height))
                    except (KeyError, ValueError) as exc:
                        raise SceneEventError(
                            "ACTOR_COMPOSITION_FAILED",
                            f"Draw {j}: recorded actor row rejected: {exc}",
                            event_index=i) from exc
                else:
                    raise SceneEventError("DRAW_KIND_UNSUPPORTED",
                                          f"Unsupported draw operation {draw['kind']!r}",
                                          event_index=i)
            yield {"tick": tick, "order": order, "indices": canvas,
                   "palette": bytes(current_palette),
                   "indexed_sha256": sha256(canvas).hexdigest(),
                   "palette_sha256": sha256(current_palette).hexdigest(),
                   "draw_count": len(draws), "evidence": sorted(seen_evidence),
                   "scene_fidelity": "NOT VALIDATED",
                   "engine_timing_inferred": False}
        else:
            raise SceneEventError("EVENT_KIND_UNSUPPORTED",
                                  f"Unsupported event kind {kind!r}", event_index=i)
