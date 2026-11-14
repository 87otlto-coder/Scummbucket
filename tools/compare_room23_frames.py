"""Verify paired frame records and compare lossless Room 23 planes with the native export."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


def digest(data):
    return hashlib.sha256(data).hexdigest()


def engine(data, expected):
    header, sep, payload = data.partition(b"\nDATA\n")
    lines = header.decode("utf8").splitlines()
    tag, *fields = lines[0].split()
    frame, ms, timer, next_timer, top, masks, render, gfx, scaler = map(int, fields)
    if tag != "R23E1" or frame != expected or not 0 <= top <= 56 or not 1 <= masks <= 8:
        raise ValueError("invalid engine geometry, phase or frame ID")
    if not sep or len(payload) != 3072 + 2*46080 + masks*5760 + 64000:
        raise ValueError("incomplete engine payload")
    meta = dict(id=frame, wall_ms=ms, timer_pair=[timer, next_timer], top=top, mask_count=masks,
                render_mode=render, gfx_mode=gfx, scaler=scaler, version=lines[1], state=lines[2:])
    palettes = [payload[n:n+768] for n in range(0, 3072, 768)]
    depth = payload[95232:-64000]
    meta["depth_sha256"] = [digest(depth[n:n+5760]) for n in range(0, len(depth), 5760)]
    return meta, palettes, payload[3072:49152], payload[49152:95232], payload[-64000:]


def present(data, expected):
    header, sep, rgb = data.partition(b"\n")
    tag, frame, ms, w, h, name = header.decode().split()
    size = int(w), int(h)
    if tag != "R23D1" or int(frame) != expected or not sep or min(size) < 1 or len(rgb) != 3*size[0]*size[1]:
        raise ValueError("invalid display payload or frame ID")
    return int(ms), name, Image.frombytes("RGB", size, rgb)


def rgb_image(size, indices, palette):
    im = Image.frombytes("P", size, indices)
    im.putpalette(palette)
    return im.convert("RGB")


def rgb_errors(a, b):
    if a.size != b.size:
        raise ValueError("unequal comparison dimensions")
    r, g, blue = ImageChops.difference(a, b).split()
    hist = ImageChops.lighter(ImageChops.lighter(r, g), blue).histogram()
    return sum(hist[1:])


def read_export(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["schema"] != "room23-background/1" or len(manifest["frames"]) != 87:
        raise ValueError("expected 87-frame Room 23 export")
    phases = {}
    for seq, item in enumerate(manifest["frames"], 1):
        raw = (folder / item["file"]).read_bytes()
        with Image.open(io.BytesIO(raw)) as im:
            indices = im.tobytes()
            palette = bytes(im.getpalette())
            if (im.mode != "P" or im.size != (320, 144) or item["sequence"] != seq or
                    digest(raw) != item["png_sha256"] or digest(indices) != manifest["index_sha256"] or
                    digest(palette) != item["palette_sha256"]):
                raise ValueError("invalid native export frame")
        phases.setdefault(palette, []).append(seq)
    return manifest, indices, phases


def compare(capture, export):
    manifest, reference, phases = read_export(export)
    run = json.loads((capture / "run.json").read_text())
    v2 = {}
    trace = capture / "scummbucket-p4-room23.raw.log"
    if not trace.exists():
        trace = trace.with_suffix(".log.tmp")
    lines = trace.read_text().splitlines()
    for line in lines:
        if line.startswith("SBP4|SAMPLE|"):
            _, _, seq, t, nt, _, pal = line.split("|")
            v2[int(seq)] = ([int(t), int(nt)], bytes.fromhex(pal))
    result = {"run": run, "same_run_v2_sha256": digest(trace.read_bytes()),
              "same_run_v2_has_end": any(line.startswith("SBP4|END|") for line in lines), "export_manifest_sha256": digest((export / "manifest.json").read_bytes()),
              "legacy_trace_sha256": manifest["raw_sha256"], "frames": []}
    for seq in range(1, 88):
        raw = (capture / f"engine-{seq:03}.bin").read_bytes()
        display = (capture / f"present-{seq:03}.bin").read_bytes()
        meta, pals, bg, front, screen = engine(raw, seq)
        pre, post, manipulated, final = pals
        when, renderer, image = present(display, seq)
        if v2.get(seq) != (meta["timer_pair"], post):
            raise ValueError(f"V2 same-run trace disagreement at {seq}")
        y = meta["top"]
        crop = screen[y*320:(y+144)*320]
        indexed = rgb_image((320, 200), screen, final)
        meta.update(engine_sha256=digest(raw), present_sha256=digest(display), present_wall_ms=when,
                    renderer=renderer, present_size=image.size, palette_hashes=[digest(p) for p in pals],
                    legacy_samples_with_exact_post_palette=phases.get(post, []),
                    background_index_errors=sum(a != b for a, b in zip(reference, bg)),
                    front_changed_from_background=sum(a != b for a, b in zip(bg, front)),
                    backend_changed_from_front=sum(a != b for a, b in zip(crop, front)),
                    render_rgb_errors=None, export_to_present_rgb_errors=None)
        if image.size == (320, 200):
            meta["render_rgb_errors"] = rgb_errors(image, indexed)
            # SDL Surface requests an RGB565 streaming texture on this SDL2 path.
            # Test the conversion independently, retaining unmodelled pixels.
            lut = [((c >> shift) * 255) // (255 >> shift)
                   for shift in (3, 2, 3) for c in range(256)]
            meta["rgb565_model_errors"] = rgb_errors(image, indexed.point(lut))
            meta["rgb565_room_model_errors"] = rgb_errors(
                image.crop((0, y, 320, y+144)), indexed.point(lut).crop((0, y, 320, y+144)))
            if post in phases:
                meta["export_to_present_rgb_errors"] = rgb_errors(
                    image.crop((0, y, 320, y+144)), rgb_image((320, 144), reference, post))
        result["frames"].append(meta)
    return result


def write_preview(capture, export, report, path):
    """Show the first exact palette match, using full native resolution."""
    item = next(row for row in report["frames"] if row["legacy_samples_with_exact_post_palette"])
    seq = item["id"]
    old = item["legacy_samples_with_exact_post_palette"][0]
    manifest = json.loads((export / "manifest.json").read_text())
    with Image.open(export / manifest["frames"][old-1]["file"]) as frame:
        background = frame.convert("RGB")
    _, _, display = present((capture / f"present-{seq:03}.bin").read_bytes(), seq)
    if display.size != (320, 200):
        raise ValueError("preview requires native-size readback")
    room = display.crop((0, item["top"], 320, item["top"]+144))
    sheet = Image.new("RGB", (960, 166))
    draw = ImageDraw.Draw(sheet)
    for i, (pic, label) in enumerate((
            (background, f"Export sample {old} (exact post-cycle palette)"),
            (room, f"SDL present {seq} (room crop)"),
            (ImageChops.difference(room, background).point(lambda n: min(255, n*4)), "RGB difference x4"))):
        sheet.paste(pic, (320*i, 0))
        draw.text((320*i+2, 147), label)
    with path.open("xb") as stream:
        sheet.save(stream, format="PNG")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "export", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    report = compare(args.capture, args.export)
    with args.output.open("x", encoding="utf8") as out:
        json.dump(report, out, indent=2)

    if args.preview:
        write_preview(args.capture, args.export, report, args.preview)
