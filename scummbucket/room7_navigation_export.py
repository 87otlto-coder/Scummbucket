"""Segment-aware Room 7 native animation manifest and local HTML player.

No game data is embedded in SOURCE. Frame pixels come from the independent
archive costume compositor; palettes are engine-observed during the capture.
Only the native 320x144 Room 7 exterior is represented. Interior ticks absent
from the source capture are NEVER silently interpolated or played over.
"""
from __future__ import annotations

import json
import re

FRAME = re.compile(r"frame-[0-9]{4}\.png\Z")

PLAYER = """<!doctype html>
<meta charset="utf-8">
<title>ScummBucket | Room 7 exterior navigation</title>
<style>
body{font:14px system-ui,sans-serif;background:#191919;color:#f5f5f5;margin:2rem}
img{display:block;width:640px;max-width:100%;height:auto;image-rendering:pixelated;
image-rendering:crisp-edges;background:black;margin:1rem 0}
select,button{font:inherit;padding:.4rem}
small{display:block;max-width:44rem;line-height:1.5;color:#c7c7c7}
</style>
<h1>Room 7 — independently reconstructed exterior</h1>
<p>Select one continuously observed exterior segment. No Room 12 frames are
present; the doorway interior gap is not synthesized.</p>
<label>Segment <select id="segment"></select></label>
<button id="play">Play</button><button id="stop">Stop</button>
<span id="status" role="status"></span>
<img id="screen" width="320" height="144" alt="Room 7 reconstructed frame">
<small>Native 320×144 indexed source pixels. Scenery and Guybrush are painted
from archive COST and ZP01. Color palettes and timings come from the recorded
ScummVM session. This player is a research preview, not a game interpreter.</small>
<script>
const segments = __ANIMATION_TIMELINE__;
const picker = document.getElementById('segment');
const screen = document.getElementById('screen');
const play = document.getElementById('play');
const stop = document.getElementById('stop');
const status = document.getElementById('status');
let token = 0;
segments.forEach((s,i) => {
  const option=document.createElement('option');
  option.value=String(i);
  option.textContent='Frames '+s.first_frame+'–'+s.last_frame+
    (s.omitted_ticks_before===null?' (start)':
       ' (after '+s.omitted_ticks_before+' unrecorded ticks)');
  picker.append(option);
});
function show(i) {
  const s=segments[Number(picker.value)], row=s.frames[i];
  screen.src=row[0];
  status.textContent='Frame '+(s.first_frame+i)+' / '+s.last_frame;
}
function halt(){token++;play.disabled=false}
picker.addEventListener('change',()=>{halt();show(0)});
stop.addEventListener('click',()=>{halt();show(0)});
play.addEventListener('click',()=>{
  halt(); const id=token;play.disabled=true;
  const s=segments[Number(picker.value)], start=performance.now();
  let last=-1;
  function draw(now){
    if(id!==token)return;
    const elapsed=now-start;
    let lo=0,hi=s.frames.length;
    while(lo<hi){const mid=(lo+hi)>>1;
      if(s.frames[mid][1]<=elapsed)lo=mid+1;else hi=mid}
    const index=Math.max(0,lo-1);
    if(index!==last){show(index);last=index}
    if(index+1<s.frames.length)requestAnimationFrame(draw);
    else play.disabled=false;
  }
  requestAnimationFrame(draw);
});
if(segments.length)show(0);else status.textContent='No verified frames';
</script>
"""


def make_segments(rows, frames):
    """Require a complete, zero-error native-frame sequence before packaging.

    Segmentation uses engine tick continuity, not walkbox changes or timestamp
    heuristics. The original Room 7 replay has one gap across Room 12.
    """
    if not rows or len(rows) != len(frames):
        raise ValueError("Need one verified exported frame for every captured row")
    result = []
    previous_tick = None
    previous_ms = None
    for seq, (row, picture) in enumerate(zip(rows, frames), 1):
        if row.get("frame") != seq or picture.get("frame") != seq:
            raise ValueError(f"Missing or reordered frame at {seq}")
        name = picture.get("file")
        if not isinstance(name, str) or name != f"frame-{seq:04d}.png" or not FRAME.fullmatch(name):
            raise ValueError(f"Unsafe frame filename at {seq}")
        comparison = row.get("comparison")
        if not isinstance(comparison, dict) or comparison.get("masked_errors") != 0:
            raise ValueError(f"Unverified indexed frame at {seq}")
        if any(not isinstance(picture.get(k), str) or
               not re.fullmatch(r"[0-9a-f]{64}", picture[k])
               for k in ("indexed_sha256", "palette_sha256", "png_sha256")):
            raise ValueError(f"Missing source hashes at {seq}")
        tick, ms = row.get("tick"), row.get("present_ms")
        if type(tick) is not int or tick < 0 or (previous_tick is not None and tick <= previous_tick):
            raise ValueError(f"Invalid engine tick at {seq}")
        if type(ms) is not int or ms < 0 or (previous_ms is not None and ms < previous_ms):
            raise ValueError(f"Nonmonotonic presentation timestamp at {seq}")
        if previous_tick is None or tick != previous_tick + 1:
            missing = None if previous_tick is None else tick - previous_tick - 1
            result.append(dict(
                segment=len(result) + 1, first_frame=seq, last_frame=seq,
                first_tick=tick, last_tick=tick, first_presentation_ms=ms,
                last_presentation_ms=ms, omitted_ticks_before=missing,
                frames=[],
            ))
        current = result[-1]
        current["last_frame"], current["last_tick"] = seq, tick
        current["last_presentation_ms"] = ms
        current["frames"].append(picture)
        previous_tick, previous_ms = tick, ms
    return result


def make_manifest(rows, frames, *, archive_hashes, capture):
    segments = make_segments(rows, frames)
    return {
        "schema": "room7-navigation-native-export/1",
        "edition": "Monkey Island 2, original DOS VGA",
        "room_id": 7,
        "geometry": [320, 144],
        "archive_sha256": archive_hashes,
        "capture": str(capture),
        "frame_count": len(frames),
        "all_indexed_comparisons_exact": True,
        "independent_picture_sources": [
            "archived Room 7 indexed SMAP background",
            "archived Room 7 ZP01 foreground mask",
            "archive-decoded COST 1 scaled and COST 142 scenery",
            "runtime-observed actor poses, scales, walkboxes and camera",
        ],
        "palette_source": "engine-observed post-presentation palette; not independently forecast here",
        "timing_source": "engine-associated SDL presentation milliseconds",
        "room12_frames_included": False,
        "gap_policy": "separate playbacks, never interpolate skipped engine ticks",
        "limitations": [
            "Valid only for this room and recorded route",
            "Original game assets and frame PNGs remain private under FIXTURE",
            "RGB/SDL display processing is not independently reconstructed",
            "No script execution or game state simulation in the HTML player",
        ],
        "segments": segments,
    }


def render_player(manifest):
    segments = manifest["segments"]
    timeline = []
    for section in segments:
        initial = section["first_presentation_ms"]
        timeline.append({
            "first_frame": section["first_frame"],
            "last_frame": section["last_frame"],
            "omitted_ticks_before": section["omitted_ticks_before"],
            "frames": [[frame["file"], frame["present_ms"] - initial] for frame in section["frames"]],
        })
    return PLAYER.replace("__ANIMATION_TIMELINE__",
                          json.dumps(timeline, separators=(",", ":")))
