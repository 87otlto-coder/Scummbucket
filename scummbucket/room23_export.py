"""Export validated Room 23 background states on the raw SBP4 time axis."""
import json
from hashlib import sha256
from pathlib import Path

from .inspector import XOR_KEY, _read_pair, inspect
from .palette_probe import decode_room_background_indexed, prepare_cycles
from .palette_sequence import encode_indexed_png
from .room23_capture_research import (
    KNOWN_DOS_VGA_MI2_SHA256, MAX_LOG_BYTES, compare_room23_palette_capture,
    iter_continuous_palettes, parse_room23_hook_log,
)

INDEX_SHA = "94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f"


def verified_frames(bg, records, capture, comparison):
    replay = comparison["continuous_scheduler"]
    if replay["status"] != "matched":
        raise ValueError("Continuous replay requires a resolved phase and an exact holdout")
    cycles, _ = prepare_cycles(records)
    rows = capture["samples"]
    states = iter_continuous_palettes(bg["initial_palette"], cycles, capture,
                                      replay["first_sample_equivalent_model_update"])
    for i, (palette, events) in enumerate(states):
        row = rows[i]
        if palette != row["palette"]:
            raise ValueError(f"Predicted palette differs at sample {i + 1}")
        png = encode_indexed_png(bg["width"], bg["height"], bg["indexed_pixels"], palette)
        yield png, {
            "sequence": i + 1, "file": f"sample-{i + 1:03d}.png",
            "millis": row["millis"], "offset_ms": row["millis"] - capture["begin_millis"],
            "until_next_ms": rows[i + 1]["millis"] - row["millis"] if i + 1 < len(rows) else None,
            "timer_pair": [row["var_timer"], row["var_timer_next"]],
            "rotation_ids": [e["cycle_id"] for e in events],
            "palette_sha256": sha256(palette).hexdigest(), "png_sha256": sha256(png).hexdigest(),
        }


def export_room23(source, raw_log, output_dir):
    source, raw_log, dest = map(Path, (source, raw_log, output_dir))
    if raw_log.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("Trace exceeds SBP4 size limit")
    capture = parse_room23_hook_log(raw_log.read_bytes())
    inventory = inspect(source)
    if inventory["status"] != "success":
        raise ValueError("Game archive failed inspection")
    index, resource, index_name, resource_name = _read_pair(source)
    hashes = [sha256(data).hexdigest() for data in (index, resource)]
    if hashes != [entry["sha256"] for entry in inventory["sources"]] or hashes[1] != KNOWN_DOS_VGA_MI2_SHA256:
        raise ValueError("Archive changed or unsupported resource edition")
    room, = (r for r in inventory["resources"]["rooms"] if r["id"] == 23)
    bg = decode_room_background_indexed(bytes(b ^ XOR_KEY for b in resource),
                                        room_offset=room["room_offset"], room_length=room["room_size"])
    if bg["pixel_indices_sha256"] != INDEX_SHA or (bg["width"], bg["height"]) != (320, 144):
        raise ValueError("Unexpected Room 23 index plane")
    records = room["palette_cycles"]
    comparison = compare_room23_palette_capture(bg["initial_palette"], records, capture)
    frames = list(verified_frames(bg, records, capture, comparison))
    replay = comparison["continuous_scheduler"]
    manifest = {
        "schema": "room23-background/1", "room": 23, "size": [320, 144],
        "archive_pair": list(zip((index_name, resource_name), hashes)),
        "raw_log": str(raw_log), "raw_sha256": capture["raw_sha256"],
        "capture_complete": capture["complete"], "stop_reason": capture["stop_reason"],
        "begin_millis": capture["begin_millis"], "index_sha256": INDEX_SHA,
        "source_offsets": bg["source"], "source_clut_sha256": bg["initial_palette_sha256"],
        "begin_palette_sha256": sha256(capture["initial_palette"]).hexdigest(),
        "source_cycles": records, "decoder_diagnostics": bg["diagnostics"],
        "method": replay["method"], "phase_search_limit": 500,
        "first_sample_equivalent_update": replay["first_sample_equivalent_model_update"],
        "calibration_samples": replay["calibration_samples"], "heldout_matches": replay["heldout_matches"],
        "noncycling_BEGIN_overrides": comparison["runtime_noncycle_overrides_vs_source_clut"],
        "clock_gaps": comparison["clock_discontinuities"], "uncomposited_zplanes": bg["background_zplanes"],
        "limitations": comparison["limitations"] + [
            "Static RMIM background only. Objects, actors, interface and display processing are omitted.",
            "Each timestamp measures a palette callback. Display time and the final hold are unknown."],
        "frames": [meta for _, meta in frames],
    }
    # Atomically reserve a fresh directory. The manifest is the completion marker.
    dest.mkdir(parents=True, exist_ok=False)
    for png, meta in frames:
        with (dest / meta["file"]).open("xb") as stream:
            stream.write(png)
    timeline = json.dumps([[m["file"], m["millis"] - frames[0][1]["millis"]] for _, m in frames])
    with (dest / "play.html").open("x", encoding="utf-8") as stream:
        stream.write(PLAYER.replace("TIMELINE", timeline))
    with (dest / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    return manifest


PLAYER = """<!doctype html><meta charset=utf-8><title>Room 23 background</title>
<style>img{image-rendering:pixelated;display:block}body{background:#171717;color:white}</style>
<img width=320 height=144 alt="Room 23 background"><button disabled>Play from sample 1</button>
<script>
const frames = TIMELINE, screenImage = document.querySelector('img'), button = document.querySelector('button');
const images = frames.map(([file]) => {const img = new Image(); img.src = file; return img});
Promise.all(images.map(img => img.decode())).then(() => {
  screenImage.src = images[0].src; button.disabled = false;
}).catch(() => button.textContent = 'Frame loading failed');
button.onclick = () => {
  button.disabled = true;
  const start = performance.now(); let index = 0;
  function draw(now) {
    while (index + 1 < frames.length && frames[index + 1][1] <= now - start) index++;
    screenImage.src = images[index].src;
    if (index + 1 < frames.length) requestAnimationFrame(draw); else button.disabled = false;
  }
  draw(start);
};
</script>"""
