"""Compare a Room 7 reference sweep and export its archive-background playback."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

from scummbucket.extraction import _write_new_verified
from scummbucket.palette_probe import advance_palette, prepare_cycles
from scummbucket.palette_sequence import encode_indexed_png
from scummbucket.room23_export import PLAYER
from tools.compare_room23_frames import digest, engine, present


def differences(expected, observed, size):
    # L represents the numeric palette index, independent of its displayed RGB.
    diff = ImageChops.difference(Image.frombytes("L", size, expected),
                                 Image.frombytes("L", size, observed))
    return dict(pixels=size[0] * size[1] - diff.histogram()[0], bbox=diff.getbbox())


def compare(capture, export, dest):
    manifest = json.loads((export / "manifest.json").read_text())
    run = json.loads((capture / "run.json").read_text())
    if run["room"] != 7 or manifest["room_id"] != 7 or set(run["archives"].values()) != {
            s["sha256"] for s in manifest["sources"]}:
        raise ValueError("Room or archive mismatch")
    for name in ("background.png", "ZP01.png"):
        if digest((export / name).read_bytes()) != manifest["files"][name]:
            raise ValueError(f"Invalid export {name}")
    with Image.open(export / "background.png") as img:
        world = img.copy()
    with Image.open(export / "ZP01.png") as img:
        mask = img.convert("1")
    if world.mode != "P" or world.size != mask.size:
        raise ValueError("Expected indexed world and aligned mask")
    trace = (capture / "scummbucket-p4-room7.raw.log").read_text().splitlines()
    samples = [line.split("|") for line in trace if line.startswith("SBP4|SAMPLE|")]
    cycles, problems = prepare_cycles(manifest["scene"]["palette_cycles"])
    if problems:
        raise ValueError(problems)
    dest.mkdir(parents=True, exist_ok=False)
    timeline, frames = [], []
    prediction = None
    for seq in range(1, 88):
        raw = (capture / f"engine-{seq:03}.bin").read_bytes()
        m, pals, back, front, backend = engine(raw, seq)
        display = (capture / f"present-{seq:03}.bin").read_bytes()
        ms, renderer, rgb = present(display, seq)
        camera, = (s.split()[1:] for s in m["state"] if s.startswith("camera "))
        cx, cy, x, y, w, h, ww, wh = map(int, camera)
        if (ww, wh) != world.size or (w, h) != (320, 144) or y != 0 or not 0 <= x <= ww-w or m["mask_count"] != 2:
            raise ValueError(f"Unexpected geometry at frame {seq}")
        rect = (x, y, x+w, y+h)
        crop = world.crop(rect).tobytes()
        packed = mask.crop(rect).tobytes()
        payload = raw.split(b"\nDATA\n", 1)[1]
        depth = payload[3072+2*w*h:-64000]
        runtime_mask = Image.frombytes("1", (w,h), depth[len(packed):]).convert("L")
        if prediction is None:
            prediction = bytearray(pals[0])
            first_ms = ms
        events = advance_palette(prediction, cycles, delta=max(m["timer_pair"]))
        sample = samples[seq-1]
        if int(sample[2]) != seq or list(map(int, sample[3:5])) != m["timer_pair"] or bytes.fromhex(sample[6]) != pals[1]:
            raise ValueError(f"Palette trace does not pair at {seq}")
        name = f"viewport-{seq:03}.png"
        png = encode_indexed_png(w, h, crop, pals[3])
        _write_new_verified(dest / name, png)
        timeline.append([name, ms-first_ms])
        top = m["top"] * w
        m.update(camera_xy=[cx,cy], viewport_xy=[x,y], present_ms=ms, renderer=renderer,
                 engine_sha256=digest(raw), present_sha256=digest(display), present_size=rgb.size,
                 palette_stages_sha256=[digest(p) for p in pals], cycle_events=[e["cycle_id"] for e in events],
                 scheduler_matches=prediction == pals[1], plane_zero_nonzero_bytes=sum(b != 0 for b in depth[:len(packed)]),
                 background=differences(crop, back, (w,h)),
                 mask=differences(mask.crop(rect).convert("L").tobytes(), runtime_mask.tobytes(), (w,h)),
                 front_vs_backend=differences(front, backend[top:top+w*h], (w,h)),
                 front_vs_background=differences(crop, front, (w,h)))
        frames.append(m)
    html = PLAYER.replace("Room 23 background", "Room 7 archive background").replace("TIMELINE", json.dumps(timeline))
    _write_new_verified(dest / "play.html", html.encode())
    report = dict(schema="room7-sweep/1", run=run, capture=str(capture), export=str(export),
                  manifest_sha256=digest((export / "manifest.json").read_bytes()), frames=frames)
    _write_new_verified(dest / "report.json", json.dumps(report, indent=2).encode())
    return frames


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("capture", "export", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    frames = compare(args.capture, args.export, args.output)
    for key in ("background", "mask", "front_vs_backend", "front_vs_background"):
        print(key, sum(m[key]["pixels"] for m in frames))
    print("continuous palette matches", sum(m["scheduler_matches"] for m in frames))
    if any(m[k]["pixels"] for m in frames for k in ("background", "mask", "front_vs_backend")):
        raise SystemExit(2)
