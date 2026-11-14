"""Private, self-contained Room 23 palette-background animation package.

Consumes an already validated native Room 23 export plus its *exact* original
SBP4 trace. No game archive is reopened; no new frames or timing are invented.
The original play.html and manifest.json are preserved unmodified.
"""
from hashlib import sha256
from pathlib import Path
import json
import re

from .native_animation_common import (
    embed_segment_timeline, frame_data_uri, inspect_indexed_png,
)
from .room23_capture_research import (
    _split_on_clock_discontinuities, parse_room23_hook_log, MAX_LOG_BYTES,
)
from .room23_export import INDEX_SHA
from .room23_capture_research import KNOWN_DOS_VGA_MI2_SHA256


INDEX_ARCHIVE_SHA = "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1"
FRAME_NAME = re.compile(r"sample-[0-9]{3}\.png\Z")
HTML_FILENAME = "play-standalone.html"
MANIFEST_FILENAME = "animation.json"

PLAYER = """<!doctype html><meta charset="utf-8">
<title>ScummBucket | Room 23 palette background</title>
<style>
body{background:#191919;color:#eee;font:14px system-ui,sans-serif;margin:2rem}
img{image-rendering:pixelated;display:block;margin:1rem 0;width:640px;
max-width:100%;height:auto}
button,select{font:inherit;padding:0.4rem;margin:0.3rem}
small{display:block;line-height:1.5;max-width:52rem;color:#ccc}
</style>
<h1>Room 23 — reconstructed background palette</h1>
<p>Choose a trace segment. A recording gap is not interpolated or treated
as proof of a script restart.</p>
<label>Segment <select id="segment"></select></label>
<button id="play">Play</button><button id="stop">Stop</button>
<span id="status" role="status"></span>
<img id="screen" width="320" height="144" alt="Original-size Room 23 indexed background">
<small>Background only. All images use the original archive-decoded 320×144
index plane. Palette snapshots come from a source-CYCL model calibrated
against the captured SBP4 callback trace. No Guybrush, objects, masks,
audio or 320×200 SDL framebuffer are reconstructed in this package.
Timing represents recorded callback timestamps, not verified screen duration.</small>
<script>
const segments=__TIMELINE__;
const picker=document.getElementById('segment');
const screen=document.getElementById('screen');
const play=document.getElementById('play');
const stop=document.getElementById('stop');
const status=document.getElementById('status');
let token=0;
segments.forEach((seg,i)=>{
  let option=document.createElement('option');
  option.value=String(i);
  option.textContent='Samples '+seg.first+'–'+seg.last+
    (seg.gap_ms_before===null?' (start)': ' (after a '+seg.gap_ms_before+' ms recording gap)');
  picker.append(option);
});
function show(i){
  const seg=segments[Number(picker.value)];
  const row=seg.frames[i];
  screen.src=row[0];
  status.textContent='Sample '+(seg.first+i)+' / '+seg.last;
}
function halt(){token++;play.disabled=false}
picker.addEventListener('change',()=>{halt();show(0)});
stop.addEventListener('click',()=>{halt();show(0)});
play.addEventListener('click',()=>{
  halt();const id=token,seg=segments[Number(picker.value)],start=performance.now();
  play.disabled=true;
  let prior=-1;
  function draw(now){
    if(id!==token)return;
    const elapsed=now-start;
    let low=0,high=seg.frames.length;
    while(low<high){
      const mid=(low+high)>>1;
      if(seg.frames[mid][1]<=elapsed)low=mid+1;else high=mid;
    }
    const i=Math.max(0,low-1);
    if(i!==prior){show(i);prior=i}
    if(i+1<seg.frames.length)requestAnimationFrame(draw);
    else play.disabled=false;
  }
  requestAnimationFrame(draw);
});
if(segments.length)show(0);else status.textContent='No verified samples';
</script>
"""


def _bounded_json(path, maximum=8*1024*1024):
    path = Path(path)
    if path.stat().st_size > maximum:
        raise ValueError(f"Manifest exceeds {maximum} bytes")
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(export_dir, raw_log):
    """Verify every sample, phase provenance and trace clock before packaging.

    Source export's phase calibration and full-palette prediction must have
    passed. This does not repeat the phase model or prove RGB display output.
    """
    folder, raw_log = Path(export_dir), Path(raw_log)
    metadata_path = folder / "manifest.json"
    original = metadata_path.read_bytes()
    if len(original) > 8*1024*1024:
        raise ValueError("Original native manifest too large")
    metadata = json.loads(original)
    if metadata.get("schema") != "room23-background/1" or metadata.get("room") != 23:
        raise ValueError("Expected existing Room 23 background export")
    if metadata.get("size") != [320, 144] or metadata.get("index_sha256") != INDEX_SHA:
        raise ValueError("Not the pinned 320x144 indexed Room 23 archive plane")
    source_hashes = metadata.get("archive_pair")
    if (not isinstance(source_hashes,list) or len(source_hashes)!=2 or
        [v[1] for v in source_hashes] != [INDEX_ARCHIVE_SHA, KNOWN_DOS_VGA_MI2_SHA256]):
        raise ValueError("Not the pinned original DOS VGA archive pair")
    if (not isinstance(metadata.get("first_sample_equivalent_update"),int) or
        metadata["first_sample_equivalent_update"] <= 0 or
        not isinstance(metadata.get("calibration_samples"),int) or
        metadata["calibration_samples"] < 2 or
        not isinstance(metadata.get("heldout_matches"),int) or
        metadata["heldout_matches"] <= 0):
        raise ValueError("Missing or unresolved palette calibration and holdout evidence")
    if raw_log.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("Private SBP4 raw log is too large")
    raw = raw_log.read_bytes()
    if sha256(raw).hexdigest() != metadata.get("raw_sha256"):
        raise ValueError("Original raw SBP4 trace hash differs from export")
    capture = parse_room23_hook_log(raw)
    if (capture["complete"] != metadata.get("capture_complete") or
        capture["begin_millis"] != metadata.get("begin_millis")):
        raise ValueError("Raw trace completion or start time differs from export")
    records = metadata.get("frames")
    if not isinstance(records,list) or not records or len(records) != len(capture["samples"]):
        raise ValueError("Export's frame count differs from the authenticated raw trace")
    _, gaps, _ = _split_on_clock_discontinuities(capture["samples"])
    if gaps != metadata.get("clock_gaps"):
        raise ValueError("Export gap annotations do not match original raw log")
    by_after = {gap["after_sequence"]: gap for gap in gaps}
    sections = []
    timeline = []
    prior_ms = None
    expected_names = set()
    for pos, (record, sample) in enumerate(zip(records,capture["samples"]),1):
        expected = f"sample-{pos:03d}.png"
        ms = sample["millis"]
        if (record.get("sequence") != pos or record.get("file") != expected or
            not FRAME_NAME.fullmatch(expected) or record.get("millis") != ms or
            record.get("offset_ms") != ms-capture["begin_millis"] or
            record.get("timer_pair") != [sample["var_timer"],sample["var_timer_next"]] or
            record.get("palette_sha256") != sha256(sample["palette"]).hexdigest() or
            (prior_ms is not None and ms < prior_ms)):
            raise ValueError(f"Sample {pos}: timestamps, timers or palette mismatch")
        next_ms = capture["samples"][pos]["millis"] if pos < len(records) else None
        if record.get("until_next_ms") != (next_ms - ms if next_ms is not None else None):
            raise ValueError(f"Sample {pos}: next timestamp interval differs")
        raw_png = inspect_indexed_png(
            folder / expected, size=(320,144), index_sha=INDEX_SHA,
            palette_sha=record["palette_sha256"], png_sha=record["png_sha256"])
        if pos == 1 or (pos-1) in by_after:
            gap = by_after.get(pos-1)
            sections.append(dict(
                segment=len(sections)+1, first=pos, last=pos,
                gap_ms_before=None if gap is None else gap["gap_ms"],
                first_ms=ms, last_ms=ms, samples=[],
            ))
            timeline.append(dict(
                first=pos, last=pos, gap_ms_before=None if gap is None else gap["gap_ms"],
                frames=[],
            ))
        sections[-1]["last"],sections[-1]["last_ms"]=pos,ms
        sections[-1]["samples"].append({
            "sequence":pos, "file":expected, "millis":ms,
            "png_sha256":record["png_sha256"],
            "indexed_sha256":INDEX_SHA,"palette_sha256":record["palette_sha256"],
        })
        timeline[-1]["last"]=pos
        timeline[-1]["frames"].append([
            frame_data_uri(raw_png),ms-sections[-1]["first_ms"],
        ])
        prior_ms = ms
        expected_names.add(expected)
    if {p.name for p in folder.glob("sample-*.png")} != expected_names:
        raise ValueError("Original Room 23 sample PNG inventory differs from manifest")
    output = {
        "schema":"room23-portable-native-background/1",
        "room_id":23,"edition":"Monkey Island 2 original DOS VGA",
        "mode":"palette_background_only","geometry":[320,144],
        "original_export_manifest_sha256":sha256(original).hexdigest(),
        "raw_capture_sha256":sha256(raw).hexdigest(),
        "archive_sha256":{"MONKEY2.000":INDEX_ARCHIVE_SHA,
                          "MONKEY2.001":KNOWN_DOS_VGA_MI2_SHA256},
        "source_index_sha256":INDEX_SHA,"capture_complete":capture["complete"],
        "stop_reason":capture["stop_reason"],"frame_count":len(records),
        "palette_source":"archive-CYCL phase calibrated against the original raw SBP4 trace",
        "timing_source":"SBP4 callback wall-clock milliseconds; not verified screen hold",
        "source_phase_calibration_samples":metadata["calibration_samples"],
        "source_heldout_matches":metadata["heldout_matches"],
        "clock_gaps":gaps,"segments":sections,
        "original_framebuffers_included":False,
        "limitations":[
            "No actors, objects, masks, foreground composition or game scripts",
            "A clock discontinuity does not prove a room/script restart",
            "No SDL output pixel-equivalence or full-scene reconstruction",
            "Original mixed SBP4 capture may be incomplete; final hold unknown",
            "Recorded callback times do not imply continuous observation across gaps",
        ],
    }
    return output, embed_segment_timeline(PLAYER,timeline,marker="__TIMELINE__")


def package(export_dir, raw_log):
    """Use exclusive creation; leave existing source frames and metadata intact."""
    folder=Path(export_dir)
    destinations=[folder/MANIFEST_FILENAME,folder/HTML_FILENAME]
    if any(path.exists() for path in destinations):
        raise FileExistsError("Portable Room 23 output already exists; do not overwrite")
    manifest,html=prepare(folder,raw_log)
    # Completion marker is the metadata JSON, last. A lone HTML indicates an
    # interrupted package and must never be mistaken for accepted output.
    with destinations[1].open("x",encoding="utf-8") as output:
        output.write(html)
    with destinations[0].open("x",encoding="utf-8") as output:
        json.dump(manifest,output,indent=2)
    return manifest
