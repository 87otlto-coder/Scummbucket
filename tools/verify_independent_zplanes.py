"""Validate independent archive-backed depth planes and existing scene replays."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.extraction import _write_new_verified
from scummbucket.inspector import XOR_KEY, _read_pair, chunks, inspect
from scummbucket.palette_probe import decode_room_background_indexed
from scummbucket.room24_water import DOS_HASHES, authored_position, decode_layer
from scummbucket.zplanes import compare_plane, compose_planes, crop_plane, pack_plane
from tools.compare_room24_capture import compare as compare24
from tools.compare_room35_capture import compare as compare35
from tools.verify_room7_scene import compare as compare7


class ArchiveDepth:
    """Render a fresh world mask from archive background and ordered object state."""

    def __init__(self, game, room_id):
        index, resource, _, _ = _read_pair(game)
        if tuple(sha256(blob).hexdigest() for blob in (index, resource)) != DOS_HASHES:
            raise ValueError("Unrecognized original MI2 DOS VGA archive pair")
        inventory = inspect(game)
        self.room_id = room_id
        room, = (r for r in inventory["scene_inventory"]["rooms"] if r["room_id"] == room_id)
        self.data = bytes(v ^ XOR_KEY for v in resource)
        offset = room["room_offset"]
        length = room["room_size"]
        bg = decode_room_background_indexed(self.data, room_offset=offset, room_length=length,
                                            include_masks=True)
        self.width, self.height = bg["width"], bg["height"]
        self.objects = {obj["object_id"]: obj for obj in room["objects"]}
        trns, = (c for c in chunks(self.data, offset + 8, offset + length, "ROOM")
                 if c.tag == "TRNS" and c.length >= 9)
        self.transparent = self.data[trns.offset + 8]
        self.background = {i: bytes(self.width // 8 * self.height)
                           for i in range(bg["zplane_count"])}
        self.sources = dict(background={}, objects={})
        for tag, plane in bg["zplane_masks"].items():
            number = int(tag[2:])
            if number not in self.background:
                raise ValueError("Background depth plane exceeds RMIH count")
            packed = pack_plane(plane["pixels"], self.width, self.height)
            self.background[number] = packed
            self.sources["background"][tag] = {
                **{k: v for k, v in plane.items() if k != "pixels"},
                "packed_sha256": sha256(packed).hexdigest(),
                "width": self.width, "height": self.height, "bit_order": "msb_left",
            }
        self.sources["room"] = bg["source"]
        self.cache = {}
        self.frames = []

    def object_mask(self, key):
        if key not in self.cache:
            number, state = key
            obj = self.objects[number]
            meta, _, _, masks = decode_layer(self.data, obj, state, self.transparent)
            width, height = meta["width"], meta["height"]
            packed = {int(tag[2:]): pack_plane(mask, width, height) for tag, mask in masks.items()}
            self.cache[key] = (width, height, packed,
                               tuple(row["transparent_codec"] for row in meta["strip_codecs"]))
            offset = meta["source_offset"]
            nodes = chunks(self.data, offset + 8, offset + meta["source_length"], "IMxx")
            self.sources["objects"][f"{number}:{state}"] = dict(
                offset=offset, width=width, height=height,
                planes={c.tag: dict(offset=c.offset, byte_length=c.length,
                                    packed_sha256=sha256(packed[int(c.tag[2:])]).hexdigest())
                        for c in nodes if c.tag in masks})
        return self.cache[key]

    def predict(self, state_rows):
        rows = [row.split() for row in state_rows]
        _, _, x, y, width, height, world_width, world_height = next(
            tuple(map(int, r[1:])) for r in rows if r[0] == "camera")
        if (world_width, world_height) != (self.width, self.height):
            raise ValueError("Capture world geometry differs from archive")
        objects = [(int(r[1]), int(r[2])) for r in rows if r[0] == "object"]
        positions = {int(r[1]): tuple(map(int, r[2:])) for r in rows if r[0] == "position"}
        if not objects or len(objects) != len({key for key, _ in objects}):
            raise ValueError("Missing or duplicate observed object slots")
        inputs = []
        layers = []
        for number, state in reversed(objects):
            obj = self.objects[number]
            # An object without any authored image cannot draw a Z plane.
            if not state or not obj["image"] or not obj["image"]["image_state_tags"]:
                continue
            if number in positions:
                ox, oy = positions[number]
            else:
                ox, oy, _ = authored_position(self.data, obj, self.room_id)
            layer = self.object_mask((number, state))
            layers.append((ox, oy, *layer))
            inputs.append(dict(object_id=number, state=state, x=ox, y=oy,
                               placement="runtime_observed" if number in positions else "archive_decoded"))
        world = compose_planes(self.background, self.width, self.height, layers)
        predicted = {n: crop_plane(mask, self.width, self.height, x=x, y=y,
                                  view_width=width, view_height=height) for n, mask in world.items()}
        return predicted, inputs, (x, y, width, height)

    def __call__(self, meta, packet):
        # No packet bytes reach the predictor. Reference bytes are isolated here.
        predicted, inputs, viewport = self.predict(meta["state"])
        _, _, width, height = viewport
        size = width // 8 * height
        start = packet.index(b"\nDATA\n") + 6 + 3072 + 2 * width * height
        if meta["mask_count"] != len(predicted):
            raise ValueError(f"Frame {meta['id']} has an unsupported runtime depth plane count")
        results = [dict(plane=n, **compare_plane(mask, packet[start + n * size:start + (n + 1) * size],
                                                 width, height)) for n, mask in sorted(predicted.items())]
        self.frames.append(dict(frame=meta["id"], viewport=viewport, objects=inputs,
                                capture_sha256=sha256(packet).hexdigest(), masks=results))
        return predicted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Canonical read-only FIXTURE root")
    parser.add_argument("capture", type=Path, help="Capture directory; Room 7 uses its pinned sweep")
    parser.add_argument("output", type=Path)
    parser.add_argument("--room", type=int, choices=(7, 24, 35), required=True)
    parser.add_argument("--waterfall-export", type=Path)
    args = parser.parse_args()
    if args.room == 35 and args.waterfall_export is None:
        parser.error("--waterfall-export is required for Room 35")
    game = args.fixture / "GAMES/MonkeyIsland2_DOS_VGA"
    masks = ArchiveDepth(game, args.room)
    args.output.mkdir(parents=True, exist_ok=False)
    if args.room == 24:
        source = compare24(game, args.capture, zplanes=masks)
        rows = source["frames"]
        back = sum(r["back"]["indices"]["mismatches"] for r in rows)
        front = sum(r["front"]["indices"]["mismatches"] for r in rows)
        palette = sum(r["front"]["palette"]["mismatches"] for r in rows)
        counters = sum(r["cycles"] != r["expected_cycles"] for r in rows)
    elif args.room == 35:
        source = compare35(game, args.waterfall_export, args.capture, zplanes=masks)
        rows = source["rows"]
        back = sum(r["extended_back"]["indices"]["mismatches"] for r in rows)
        front = sum(r["extended_front"]["indices"]["mismatches"] for r in rows)
        palette = sum(r["extended_front"]["palette"]["mismatches"] for r in rows)
        counters = sum(r["predicted_counters"] != [c[2] for c in r["engine_cycles"]] for r in rows)
    else:
        expected = args.fixture / "CAPTURES/Room7/sweep-20261110-a"
        if args.capture.resolve() != expected.resolve():
            raise ValueError("Room 7 expects its pinned sweep")
        rows = list(compare7(args.fixture, args.output / "replay", zplanes=masks))
        back = 0  # The existing verifier fails on any back-buffer mismatch.
        front = sum(r["mismatches"] for r in rows)
        source = dict(rows=rows, unmasked=sum(r["unmasked"] for r in rows))
        palette = 0  # The existing verifier fails on any final palette mismatch.
        counters = None  # Room 7 packets lack cycle-counter samples.
    summary = {key: sum(plane[key] for row in masks.frames for plane in row["masks"])
               for key in ("bytes_compared", "bits_compared", "bytes_mismatched", "bits_mismatched")}
    summary.update(frames=len(rows), back_mismatches=back, front_mismatches=front,
                   final_palette_mismatches=palette, counter_mismatch_frames=counters)
    root = Path(__file__).resolve().parents[1]
    decoder_files = ("object_images.py", "palette_probe.py", "zplanes.py")
    decoder_hashes = {name: sha256((root / "scummbucket" / name).read_bytes()).hexdigest()
                      for name in decoder_files}
    report = dict(room=args.room, edition="MI2 original DOS VGA", archive_sha256=DOS_HASHES,
                  capture=args.capture.name, evidence=["archive_decoded", "engine_source_backed",
                                                     "runtime_observed"],
                  decoder_sha256=decoder_hashes, room_source=masks.sources, frames=masks.frames, replay=source, summary=summary)
    _write_new_verified(args.output / "report.json", json.dumps(report, indent=2).encode())
    print(json.dumps(summary))
    if args.room == 7:
        print("Room 7 unmasked mismatches:", source["unmasked"])
    return int(bool(back or front or palette or counters or summary["bytes_mismatched"] or
                    (args.room == 7 and (len(rows) != 87 or source["unmasked"] != 778))))


if __name__ == "__main__":
    raise SystemExit(main())
