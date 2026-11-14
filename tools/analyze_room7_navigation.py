"""Compare the private Room 7 navigation trace to the original indexed assets."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw
from scummbucket.classic_costume import ClassicCostume, compose
from scummbucket.classic_scale import paint_scaled
from scummbucket.inspector import inspect, XOR_KEY
from scummbucket.room7_navigation_export import make_manifest, render_player
from tools.compare_room23_frames import engine, present
from tools.run_room23_frames import ARCHIVES, digest


def fields(lines, prefix, size):
    row, = (line for line in lines if line.startswith(prefix + " "))
    values = list(map(int, row[len(prefix):].split()))
    if len(values) != size:
        raise ValueError(f"Invalid {prefix} record")
    return values


def transition(previous, current):
    if previous is None or current["tick"] != previous["tick"] + 1:
        return "segment_start"
    if current["walkbox"] != previous["walkbox"]:
        return "walkbox_change"
    return None


def walk_stops(costume, facing):
    """Read stop commands from the archive's walk animation initialization."""
    direction = {270:0, 90:1, 180:2, 0:3}[facing]
    pos = costume.pointer(costume.table_start + 34 + 2*(8 + direction))
    mask = int.from_bytes(costume.data[pos:pos+2], "little")
    pos += 2
    stops = 0
    for limb in range(16):
        if mask & (0x8000 >> limb):
            command = int.from_bytes(costume.data[pos:pos+2], "little")
            pos += 2
            if command != 65535:
                pos += 1
                if costume.data[costume.commands + command] == 0x79:
                    stops |= 1 << limb
    return stops


def analyze(fixture, capture, dest, *, export_native=False):
    game = fixture / "GAMES/MonkeyIsland2_DOS_VGA"
    if any(digest(game / name) != value for name, value in ARCHIVES.items()):
        raise ValueError("Archive hash mismatch")
    entries = inspect(game)["directory_links"]["entries"]
    archive = (game / "MONKEY2.001").read_bytes()
    costumes = {}
    for number in (1, 142):
        entry, = (r for r in entries if r["directory"] == "DCOS" and r["id"] == number)
        offset = entry["source_offset"]
        costumes[number] = ClassicCostume(bytes(b ^ XOR_KEY for b in archive[offset:offset+entry["byte_length"]]))
    export = fixture / "OUTPUT/Room7/native-20261110-a"
    with Image.open(export / "background.png") as im:
        world = im.copy()
    with Image.open(export / "ZP01.png") as im:
        mask = im.convert("1")
    if sha256(world.tobytes()).hexdigest() != "843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc":
        raise ValueError("Unexpected background")
    files = sorted(capture.glob("engine-*.bin"), key=lambda p: int(p.stem.split("-")[1]))
    if not files or len(files) != len(list(capture.glob("present-*.bin"))):
        raise ValueError("Need matching engine and presentation records")
    dest.mkdir(parents=True, exist_ok=False)
    rows = []
    exported = []
    route = world.convert("RGB")
    route_pen = ImageDraw.Draw(route)
    retained = None
    for seq, file in enumerate(files, 1):
        raw = file.read_bytes()
        meta, palettes, back, front, backend = engine(raw, seq)
        presentation = (capture / f"present-{seq:03}.bin").read_bytes()
        ms, _, _ = present(presentation, seq)
        state = meta["state"]
        x, y, visible, costume, frame, box, force = fields(state, "actor 1", 7)
        camera = fields(state, "camera", 8)
        cx, cy = camera[2:4]
        if camera[4:] != [320,144,784,144] or cy or not 0 <= cx <= 464:
            raise ValueError(f"Unsupported viewport at {seq}")
        cut = (cx,0,cx+320,144)
        z = mask.crop(cut)
        if (world.crop(cut).tobytes() != back or meta["depth_sha256"] !=
                [sha256(bytes(5760)).hexdigest(), sha256(z.tobytes()).hexdigest()] or
                backend[meta["top"]*320:(meta["top"]+144)*320] != front):
            raise ValueError(f"Background, mask or backend mismatch at {seq}")
        tick, moving, facing, elevation, ignore, counter, never = fields(state, "navigation", 7)
        row = dict(frame=seq, tick=tick, present_ms=ms, world=[x,y], screen=[x-cx,y-elevation],
                   camera=camera[:2], viewport=[cx,cy], walkbox=box, scale=fields(state,"scale 1",2),
                   visible=visible, costume=costume, logical_frame=frame, moving=moving, facing=facing,
                   elevation=elevation, ignore_boxes=ignore, never_clip=never, force_clip=force,
                   animation_counter=counter, engine_sha256=sha256(raw).hexdigest(),
                   present_sha256=sha256(presentation).hexdigest())
        prev = rows[-1] if rows else None
        row["transition"] = transition(prev,row)
        if row["transition"] == "segment_start":
            retained = None
        else:
            route_pen.line([tuple(prev["world"]), (x,y)],fill="yellow")
        draw = fields(state,"draw",23) if any(s.startswith("draw ") for s in state) else None
        row["draw"] = draw
        if draw:
            stops = walk_stops(costumes[1],draw[5]) if frame == 2 else 0
            retained = (draw, cx, stops)
        row["comparison"] = None
        if visible and retained:
            pose, old_cx, stops = retained
            dx, dy, plane, sx, sy, direction, cost = pose[:7]
            if cost != 1 or sx != sy or plane not in (0,1):
                raise ValueError(f"Unsupported draw at {seq}")
            ax, ay, av, ac, *_ = fields(state,"actor 11",7)
            scenery = back
            if av and ac == 142:
                scenery, _ = compose(costumes[142],back,320,ax-cx,ay,180,[0]+[65535]*15)
            elif av:
                raise ValueError(f"Unsupported scenery at {seq}")
            pixels = bytearray(scenery)
            positions = [65535 if stops & (1 << i) else cursor for i,cursor in enumerate(pose[7:])]
            paint_scaled(costumes[1],pixels,320,dx+old_cx-cx,dy,direction,positions,sx)
            unmasked = Image.frombytes("L",(320,144),bytes(pixels))
            masked = Image.composite(Image.frombytes("L",(320,144),scenery), unmasked,z) if plane else unmasked
            actual = Image.frombytes("L",(320,144),front)
            delta = ImageChops.difference(masked,actual)
            changed = ImageChops.difference(masked,unmasked)
            mismatch = 46080-delta.histogram()[0]
            affected = 46080-changed.histogram()[0]
            row["comparison"] = dict(masked_errors=mismatch, visible_index_changes=affected,
                unmasked_errors=46080-ImageChops.difference(unmasked,actual).histogram()[0],
                bbox_screen=changed.getbbox(), plane=plane, retained_pose=draw is None,
                archive_walk_stop_bits=stops)
            if mismatch:
                delta.save(dest / f"errors-{seq:04}.png")
            elif export_native:
                if len(palettes[3]) != 768:
                    raise ValueError(f"Invalid 256-color runtime palette at {seq}")
                raster = masked.tobytes()
                frame_image = Image.frombytes("P", (320, 144), raster)
                frame_image.putpalette(palettes[3])
                filename = f"frame-{seq:04}.png"
                path = dest / filename
                with path.open("xb") as output:
                    frame_image.save(output, format="PNG")
                exported.append(dict(
                    frame=seq, file=filename, present_ms=ms,
                    indexed_sha256=sha256(raster).hexdigest(),
                    palette_sha256=sha256(palettes[3]).hexdigest(),
                    png_sha256=sha256(path.read_bytes()).hexdigest(),
                ))
            if affected and draw:
                overlay = Image.frombytes("P",(320,144),front)
                overlay.putpalette(palettes[-1])
                overlay = overlay.convert("RGB")
                overlay.paste("magenta",mask=changed.point(lambda v: 255 if v else 0))
                ImageDraw.Draw(overlay).point(tuple(row["screen"]),fill="lime")
                overlay.save(dest / f"mask-{seq:04}.png")
        rows.append(row)
    route.save(dest / "route.png")
    report = dict(schema="room7-navigation/1", run=json.loads((capture/"run.json").read_bytes()),
                  provenance="saved-game replay with ordinary clicks; no synchronization with reference video",
                  draw_fields=["screen_x","draw_y","plane","scale_x","scale_y","facing","costume","16 limb cursors"],
                  rows=rows)
    (dest / "navigation.json").write_text(json.dumps(report),encoding="utf8")
    failures = [r["frame"] for r in rows if r["comparison"] is None or r["comparison"]["masked_errors"]]
    if failures:
        raise ValueError(f"Unverified indexed frames: {len(failures)}, first {failures[0]}. See {dest}")
    if export_native:
        manifest = make_manifest(rows, exported, archive_hashes=ARCHIVES, capture=capture)
        with (dest / "play.html").open("x", encoding="utf-8") as output:
            output.write(render_player(manifest))
        # The manifest is the final completion marker; partial frames do not
        # constitute an accepted export when validation aborts earlier.
        with (dest / "animation.json").open("x", encoding="utf-8") as output:
            json.dump(manifest, output, indent=2)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture","capture","dest"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--export-native", action="store_true", help="Emit exact indexed Room 7 exterior frames, segmented HTML player and manifest")
    args = parser.parse_args()
    analyze(args.fixture,args.capture,args.dest,export_native=args.export_native)
