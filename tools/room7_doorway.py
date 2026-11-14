"""Validate a continuous doorway trace and encode timestamped SDL readbacks."""
import argparse
from itertools import groupby
import json
from pathlib import Path
import subprocess

from tools.compare_room23_frames import present
from tools.instrument_room7_doorway import BUILD
from tools.run_room23_frames import digest


def read_ticks(lines):
    ticks = {}
    for line in lines:
        *fields, draw = line.rstrip("\r\n").split("\t")
        tick, room, actor_room, x, y, box, cx, cy, left, top, sx, sy = map(int, fields)
        if ticks and tick != next(reversed(ticks)) + 1:
            raise ValueError(f"Missing or repeated tick at {tick}")
        plane = None
        if draw:
            tag, *pose = draw.split()
            if tag != "draw" or len(pose) != 23:
                raise ValueError(f"Invalid draw at {tick}")
            plane = int(pose[2])
        ticks[tick] = dict(room=room, actor_room=actor_room, world=[x,y], walkbox=box,
                           camera=[cx,cy], viewport=[left,top], scale=[sx,sy], draw_plane=plane)
    rooms = [r for r, _ in groupby(row["room"] for row in ticks.values())]
    if len(rooms) != 3 or rooms[0] != 7 or rooms[1] <= 0 or rooms[2] != 7:
        raise ValueError(f"Expected Room 7, one occupied interior, Room 7. Observed {rooms}")
    if not all(any(row["actor_room"] == r and row["room"] == r for row in ticks.values())
               for r in rooms):
        raise ValueError("Missing actor in an observed room")
    return ticks


def finish(root, capture, report):
    report.mkdir(exist_ok=False)
    ticks = read_ticks((capture / "ticks.tsv").read_text().splitlines())
    rows = []
    concat = ["ffconcat version 1.0"]
    images = list(capture.glob("present-*.bin"))
    for seq, line in enumerate((capture / "presents.tsv").read_text().splitlines(), 1):
        number, tick, ms = map(int, line.split())
        if number != seq or (rows and (ms <= rows[-1]["ms"] or tick < rows[-1]["tick"])):
            raise ValueError(f"Invalid presentation timing or sequence at {seq}")
        # A final quit loop may present before returning without a completed tick.
        if tick not in ticks and tick != max(ticks) + 1:
            raise ValueError(f"No engine tick for presentation {seq}")
        raw = capture / f"present-{seq:03}.bin"
        timestamp, _, image = present(raw.read_bytes(), seq)
        if timestamp != ms:
            raise ValueError(f"SDL timestamp mismatch at {seq}")
        if rows:
            concat.append(f"duration {(ms - rows[-1]['ms']) / 1000:.3f}")
        filename = f"rgb-{seq:05}.png"
        image.save(report / filename)
        concat.extend([f"file {filename}", "option framerate 1000"])
        rows.append(dict(frame=seq, tick=tick, ms=ms, sha256=digest(raw)))
    if len(rows) >= 4800 or max(ticks) >= 2400:
        raise ValueError("Doorway capture reached its recording limit")
    if len(images) != len(rows) or not rows:
        raise ValueError("Incomplete SDL presentation inventory")
    segments = [list(group) for _, group in groupby(ticks, key=lambda tick: ticks[tick]["room"])]
    for segment in segments:
        if not any(segment[0] <= row["tick"] <= segment[-1] for row in rows):
            raise ValueError("Room segment has no synchronized presentation")
    (report / "frames.ffconcat").write_text("\n".join(concat) + "\n", encoding="ascii")
    (report / "doorway.json").write_text(json.dumps(dict(ticks=ticks, presents=rows)), encoding="utf8")
    ffmpeg = root / "TOOLS/room23-video-0.6.0/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
    with (report / "video.log").open("xb") as log:
        def run(args):
            subprocess.run([str(ffmpeg), "-nostdin", "-n", *args], cwd=report, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        run(["-safe", "0", "-f", "concat", "-i", "frames.ffconcat", "-fps_mode", "passthrough",
             "-enc_time_base", "1:1000", "-c:v", "ffv1", "-pix_fmt", "bgr0", "doorway.mkv"])
        run(["-i", "doorway.mkv", "-fps_mode", "passthrough", "-enc_time_base", "1:1000",
             "-pix_fmt", "rgb24", "-f", "framehash", "decoded.txt"])
    from hashlib import sha256
    from PIL import Image
    manifest = (report / "decoded.txt").read_text().splitlines()
    if "#tb 0: 1/1000" not in manifest:
        raise ValueError("Unexpected video time base")
    decoded = [line.split(",") for line in manifest if not line.startswith("#")]
    for seq, (frame, row) in enumerate(zip(decoded, rows, strict=True), 1):
        with Image.open(report / f"rgb-{seq:05}.png") as im:
            if (int(frame[2]) != row["ms"] - rows[0]["ms"] or
                    frame[-1].strip() != sha256(im.tobytes()).hexdigest()):
                raise ValueError(f"Decoded video differs at presentation {seq}")
    print(f"Verified {len(rows)} presentations and {len(ticks)} engine ticks in {report}")


if __name__ == "__main__":
    from tools.capture_room7_navigation import capture
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    capture(args.root.resolve(), BUILD, doorway=True)
