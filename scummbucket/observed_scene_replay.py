"""Replay explicit draw snapshots; no script execution or timing prediction.

Recorded screen coordinates already include the camera transform. Only the
archive background and masks are cropped by the observed camera rectangle.
Palette snapshots remain separate from the reconstructed native indices.
"""
from copy import deepcopy
from hashlib import sha256

from .ordered_scene_events import render_scene_event_frames


def observed_frame_packet(*, frame_id, tick, room_id, viewport, actors, palette,
                          raw_sha256):
    """Build independently replayable events from one observed engine snapshot.

    Tick is an identity, not a duration. Full palette snapshots deliberately
    avoid assuming that unrecorded transitions between samples are known.
    An empty actor list stays empty; no cached pose is silently inserted.
    """
    if any(type(v) is not int or v < 0 for v in (frame_id, tick, room_id)) or frame_id == 0:
        raise ValueError("Invalid observed frame/tick/room identity")
    if (not isinstance(viewport, (list, tuple)) or len(viewport) != 4 or
            any(type(v) is not int for v in viewport) or
            min(viewport[:2]) < 0 or min(viewport[2:]) < 1):
        raise ValueError("Invalid observed camera viewport")
    if not isinstance(actors, list) or len(actors) > 256 or any(not isinstance(a, dict) for a in actors):
        raise ValueError("Invalid observed ordered actor list")
    if not isinstance(palette, bytes) or len(palette) != 768:
        raise ValueError("Complete observed palette required")
    if (not isinstance(raw_sha256, str) or len(raw_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in raw_sha256)):
        raise ValueError("Original raw frame SHA-256 required")
    common = dict(tick=tick, evidence="engine_observed")
    return dict(schema="scummbucket-observed-frame-events/1", room_id=room_id,
                indexed_frame=frame_id, raw_sha256=raw_sha256,
                viewport=list(viewport), timing="observed_tick_identity_only",
                object_visibility="not_inferred",
                events=[dict(common, order=0, kind="palette_patch", entries=[
                    dict(index=i, rgb=list(palette[i*3:i*3+3])) for i in range(256)]),
                        dict(common, order=1, kind="frame", draw_order=[
                            dict(kind="actor", row=deepcopy(a)) for a in actors])])


def replay_observed_frame(scene, costumes, packet, *, mask_enabled=True):
    """Reconstruct from archive components and explicit events, never a frontbuffer.

    Validation against the original engine indices is performed separately.
    This function does not mark its own result verified.
    """
    if packet.get("schema") != "scummbucket-observed-frame-events/1":
        raise ValueError("Unsupported observed frame schema")
    if scene["manifest"].get("room_id") != packet.get("room_id"):
        raise ValueError("Observed frame belongs to a different source room")
    if not mask_enabled:
        # Negative control preserves valid plane references but disables pixels.
        scene = dict(scene, masks={p: bytes(len(m)) for p, m in scene["masks"].items()})
    frames = list(render_scene_event_frames(scene, {}, costumes, packet["events"],
                                           viewport=tuple(packet["viewport"])))
    if len(frames) != 1:
        raise ValueError("Observed snapshot must produce exactly one frame")
    frame = frames[0]
    frame["raw_sha256"] = packet["raw_sha256"]
    frame["indexed_frame"] = packet["indexed_frame"]
    return frame


def compare_native_frame(frame, reference_indices, reference_palette):
    """Compare independently supplied native pixels and palette, without RGB fitting."""
    if (not isinstance(reference_indices, bytes) or
            len(frame["indices"]) != len(reference_indices) or
            not isinstance(reference_palette, bytes) or len(reference_palette) != 768):
        raise ValueError("Invalid independent reference dimensions/palette")
    return dict(indexed_errors=sum(a != b for a, b in zip(frame["indices"], reference_indices)),
                palette_byte_errors=sum(a != b for a, b in zip(frame["palette"], reference_palette)),
                predicted_indexed_sha256=frame["indexed_sha256"],
                reference_indexed_sha256=sha256(reference_indices).hexdigest(),
                predicted_palette_sha256=frame["palette_sha256"],
                reference_palette_sha256=sha256(reference_palette).hexdigest())
