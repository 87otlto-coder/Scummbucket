"""Compare a separately recorded Room 23 video to an exported background sequence."""
import argparse
import hashlib
import io
import json
import statistics
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


def crop_native(image, x, y, scale):
    return image.crop((x, y, x + 320 * scale, y + 144 * scale)).resize(
        (320, 144), Image.Resampling.BOX)


def align(reference, source, origin, scale):
    x, y = origin
    candidates = []
    sky = source.crop((0, 0, 320, 40))
    for dx in range(x - 4, x + 5):
        for dy in range(y - 4, y + 5):
            if dx < 0 or dy < 0 or dx + 320*scale > reference.width or dy + 144*scale > reference.height:
                continue
            crop = crop_native(reference, dx, dy, scale).crop((0, 0, 320, 40))
            error = sum(ImageStat.Stat(ImageChops.difference(crop, sky)).sum)
            candidates.append((error, dx, dy))
    _, dx, dy = min(candidates)
    return dx, dy


def compare(args):
    manifest = json.loads((args.export / "manifest.json").read_text())
    palettes = []
    for frame in manifest["frames"]:
        data = (args.export / frame["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != frame["png_sha256"]:
            raise ValueError("Export frame hash mismatch")
        with Image.open(io.BytesIO(data)) as im:
            indices = im.tobytes()
            if im.mode != "P" or hashlib.sha256(indices).hexdigest() != manifest["index_sha256"]:
                raise ValueError("Index plane mismatch")
            palettes.append(im.getpalette())
    cycle = {i for c in manifest["source_cycles"] for i in range(c["start_color"], c["end_color"] + 1)}
    groups = {"cycle": [], "actor_box_noncycle": [], "cabin_box_noncycle": [], "other_noncycle": []}
    for pos, index in enumerate(indices):
        y, x = divmod(pos, 320)
        if index in cycle:
            group = "cycle"
        elif 30 <= x <= 74 and 88 <= y <= 143:
            group = "actor_box_noncycle"
        elif 126 <= x <= 176 and 43 <= y <= 82:
            group = "cabin_box_noncycle"
        else:
            group = "other_noncycle"
        groups[group].append(pos)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"video_sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
              "video": args.video.name, "export_trace_sha256": manifest["raw_sha256"],
              "ffmpeg": subprocess.check_output([args.ffmpeg, "-version"], text=True).splitlines()[0],
              "origin_seed": args.origin, "scale": args.scale,
              "method": "First reference sets crop by minimum sky RGB L1 within +/-4 pixels. "
                        "Choose earliest minimum-error exported frame on CYCL positions only, independently per timestamp. "
                        "Report max-channel absolute RGB errors; rectangles are spatial proxies.",
              "samples": []}
    sheet = Image.new("RGB", (960, len(args.seconds) * 164))
    source = Image.frombytes("P", (320, 144), indices)
    source.putpalette(palettes[0])
    for n, second in enumerate(args.seconds):
        data = subprocess.check_output([args.ffmpeg, "-v", "error", "-ss", str(second), "-i", str(args.video),
                                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"])
        ref = Image.open(io.BytesIO(data)).convert("RGB")
        if n == 0:
            origin = align(ref, source.convert("RGB"), args.origin, args.scale)
            report["crop_origin"] = origin
        ref = crop_native(ref, *origin, args.scale)
        rgb = ref.tobytes()

        def score(palette):
            return sum(abs(rgb[3*p+k] - palette[3*indices[p]+k]) for p in groups["cycle"] for k in range(3))

        best = min(range(len(palettes)), key=lambda i: score(palettes[i]))
        source.putpalette(palettes[best])
        prediction = source.convert("RGB")
        diff = ImageChops.difference(ref, prediction)
        channels = diff.split()
        errors = ImageChops.lighter(ImageChops.lighter(*channels[:2]), channels[2]).tobytes()
        summary = {}
        for name, positions in groups.items():
            values = [errors[p] for p in positions]
            summary[name] = {"pixels": len(values), "median": statistics.median(values),
                             "exact": values.count(0), "at_least_20": sum(v >= 20 for v in values)}
        report["samples"].append({"video_second": second, "closest_export_sample": best + 1, "regions": summary})
        for col, (img, label) in enumerate(((prediction, f"Export {best+1}"), (ref, f"Video {second}s"),
                                            (diff.point(lambda v: min(255, v*4)), "Absolute RGB difference x4"))):
            sheet.paste(img, (col*320, n*164))
            ImageDraw.Draw(sheet).text((col*320, n*164+145), label)
    sheet.save(args.output / "comparison.png")
    (args.output / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("export", "video", "output", "ffmpeg"):
        parser.add_argument("--" + field, required=True, type=Path)
    parser.add_argument("--origin", nargs=2, type=int, required=True)
    parser.add_argument("--scale", type=int, choices=(1, 2), required=True)
    parser.add_argument("--seconds", nargs="+", required=True, type=int)
    compare(parser.parse_args())
