"""Export archive-native room layers with full world coordinates."""
from hashlib import sha256
import json
from pathlib import Path
import struct

from .extraction import _write_new_verified
from .inspector import XOR_KEY, chunks, inspect, _read_pair
from .object_images import ImageDecodeError, _decode_zplane, decode_object_state, encode_png
from .palette_probe import decode_room_background_indexed
from .palette_sequence import encode_indexed_png


def export_panorama(source, output, room_id):
    src, dest = Path(source), Path(output)
    inventory = inspect(src)
    if inventory["status"] != "success":
        raise ValueError(f"Inspection failed: {inventory['diagnostics']}")
    index, resource, _, _ = _read_pair(src)
    if [sha256(buf).hexdigest() for buf in (index, resource)] != [
            row["sha256"] for row in inventory["sources"]]:
        raise ValueError("Archive changed during inspection")
    scene = next((r for r in inventory["scene_inventory"]["rooms"] if r["room_id"] == room_id), None)
    if scene is None:
        raise ValueError(f"Room {room_id} absent")
    data = bytes(b ^ XOR_KEY for b in resource)
    start, size = scene["room_offset"], scene["room_size"]
    bg = decode_room_background_indexed(data, room_offset=start, room_length=size)
    width, height = bg["width"], bg["height"]
    clut = bg["initial_palette"]
    nodes = chunks(data, start + 8, start + size, "ROOM")
    trns, = (n for n in nodes if n.tag == "TRNS")
    transparent = data[trns.offset + 8]
    dest.mkdir(parents=True, exist_ok=False)
    files = {}

    def write(name, contents):
        files[name] = _write_new_verified(dest / name, contents)

    write("background.png", encode_indexed_png(width, height, bg["indexed_pixels"], clut))
    manifest = {k: v for k, v in bg.items() if k not in ("indexed_pixels", "initial_palette")}
    manifest.update(schema="archive-panorama/1", room_id=room_id, sources=inventory["sources"],
                    scene=scene, transparent_index=transparent, masks=[], object_images=[], files=files,
                    room_children=[dict(tag=n.tag, offset=n.offset, length=n.length,
                                        decoded_sha256=sha256(data[n.offset:n.end]).hexdigest()) for n in nodes])
    im = bg["source"]["im00_offset"]
    for n in chunks(data, im + 8, im + struct.unpack_from(">I", data, im + 4)[0], "IM00"):
        if n.tag in bg["background_zplanes"]:
            try:
                mask = _decode_zplane(data, n, width=width, height=height)
                write(n.tag + ".png", encode_png(width, height, mask, rgba=False))
                manifest["masks"].append(dict(tag=n.tag, offset=n.offset, length=n.length,
                                              size=[width, height], set_pixels=mask.count(255)))
            except ImageDecodeError as exc:
                manifest["diagnostics"].append(dict(tag=n.tag, code=exc.code, message=str(exc)))
    for obj in scene["objects"]:
        image = obj["image"]
        if image is None:
            continue
        for state in image["image_state_tags"]:
            name = f"object-{obj['object_id']}-{state}"
            try:
                meta, png, masks = decode_object_state(data, obim_offset=image["source_offset"],
                                                       state_tag=state, palette=clut, transparent_color=transparent)
                write(name + ".png", png)
                for tag, mask_png in masks.items():
                    write(f"{name}-{tag}.png", mask_png)
                manifest["object_images"].append(meta)
            except ImageDecodeError as exc:
                manifest["diagnostics"].append(dict(object_state=name, code=exc.code, message=str(exc)))
    _write_new_verified(dest / "manifest.json", json.dumps(manifest, indent=2).encode())
    return manifest
