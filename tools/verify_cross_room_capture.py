"""Verify raw indexed Room 7/12 recorder data without claiming scene fidelity.

Read original engine-*.bin and present-*.bin files; preserve room/tick IDs
and ordered actor draw rows. Cross-room rendering acceptance is a later,
separate pixel comparison against the exact indexed front buffers.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from tools.compare_room23_frames import engine, present
from tools.room7_doorway import read_ticks


ENGINE_RE=re.compile(r"engine-([0-9]+)\.bin\Z")
PRESENT_RE=re.compile(r"present-([0-9]+)\.bin\Z")


def indexed_files(folder, pattern):
    pairs=[]
    for item in folder.iterdir():
        m=pattern.fullmatch(item.name)
        if m:
            pairs.append((int(m.group(1)),item))
    pairs.sort()
    if not pairs or [seq for seq,_ in pairs]!=list(range(1,len(pairs)+1)):
        raise ValueError("Missing or duplicate sequential raw capture records")
    return pairs


def parse_draw_actor(line):
    fields=line.split()
    if len(fields)!=59 or fields[0]!="draw_actor":
        raise ValueError(f"Invalid draw_actor record width: {len(fields)-1}")
    try:
        values=[int(x,10) for x in fields[1:]]
    except ValueError as exc:
        raise ValueError("Noninteger draw_actor field") from exc
    actor,x,y,plane,sx,sy,facing,cost,frame,stopped=values[:10]
    if (not 0<=actor<256 or not -4096<=x<=4096 or not -4096<=y<=4096 or
        not 0<=plane<=8 or not 0<=sx<=255 or not 0<=sy<=255 or
        facing not in (0,90,180,270) or not 0<=cost<=65535 or
        not 0<=frame<=65535 or not 0<=stopped<=0xffffffff or
        any(not 0<=n<=0xffffffff for n in values[10:])):
        raise ValueError(f"Out-of-range draw_actor {actor}")
    return dict(id=actor, screen_x=x, draw_y=y, plane=plane,
                scales=[sx,sy],facing=facing,costume=cost,
                logical_frame=frame,stopped=stopped,
                cursors=values[10:26],palette_override=values[26:58])


def read_presents(folder,ticks):
    result=[]
    index=(folder/"presents.tsv").read_text(encoding="utf-8").splitlines()
    files=indexed_files(folder,PRESENT_RE)
    if len(index)!=len(files):
        raise ValueError("SDL index/file count mismatch")
    previous_ms=None
    previous_tick=None
    for n,(line,(_,path)) in enumerate(zip(index,files),1):
        parts=line.split()
        if len(parts)!=3:raise ValueError("Invalid SDL index row")
        seq,tick,ms=map(int,parts)
        if seq!=n or tick not in ticks and tick!=max(ticks)+1:
            raise ValueError(f"SDL sequence or unknown tick: {n}")
        if (previous_ms is not None and ms<=previous_ms or
            previous_tick is not None and tick<previous_tick):
            raise ValueError(f"SDL timestamp/tick regression at {n}")
        raw=path.read_bytes()
        decoded_ms,backend,image=present(raw,n)
        if decoded_ms!=ms or image.size!=(320,200):
            raise ValueError(f"SDL raw presentation mismatch at {n}")
        result.append(dict(sequence=n,tick=tick,millis=ms,backend=backend,
                           raw_sha256=sha256(raw).hexdigest()))
        previous_ms,previous_tick=ms,tick
    return result


def verify(capture,report):
    capture,report=Path(capture),Path(report)
    run=json.loads((capture/"run.json").read_text(encoding="utf-8"))
    if run.get("capture_mode")!="cross_room" or run.get("indexed_rooms")!=[7,12]:
        raise ValueError("Not a cross-room indexed capture")
    if not all((capture/name).exists() for name in ("capture.enabled","doorway.enabled")):
        raise ValueError("Both indexed and doorway capture markers are required")
    ticks=read_ticks((capture/"ticks.tsv").read_text(encoding="utf-8").splitlines())
    presentations=read_presents(capture,ticks)
    engine_rows=[]
    rooms=Counter()
    actor_ids=Counter()
    tick_index=Counter()
    for number,path in indexed_files(capture,ENGINE_RE):
        raw=path.read_bytes()
        meta,palettes,background,front,backend=engine(raw,number)
        if len(front)!=46080 or any(len(x)!=768 for x in palettes):
            raise ValueError(f"Indexed image or palette missing at {number}")
        cut=backend[meta["top"]*320:(meta["top"]+144)*320]
        if cut!=front:
            raise ValueError(f"Indexed room/backend crop mismatch at {number}")
        scenes=[line for line in meta["state"] if line.startswith("scene ")]
        if len(scenes)!=1:
            raise ValueError(f"Missing/duplicate scene identity in indexed engine frame {number}")
        label=scenes[0].split()
        if len(label)!=3:
            raise ValueError(f"Invalid scene identity at {number}")
        room,tick=map(int,label[1:])
        if room not in (7,12) or tick not in ticks or ticks[tick]["room"]!=room:
            raise ValueError(f"Scene/engine tick linkage mismatch at indexed frame {number}")
        draws=[parse_draw_actor(line) for line in meta["state"]
               if line.startswith("draw_actor ")]
        engine_rows.append(dict(indexed_frame=number,room=room,tick=tick,
                 captured_ms=meta["wall_ms"],
                 raw_sha256=sha256(raw).hexdigest(),
                 front_sha256=sha256(front).hexdigest(),
                 background_sha256=sha256(background).hexdigest(),
                 final_palette_sha256=sha256(palettes[3]).hexdigest(),
                 depth_sha256=meta["depth_sha256"],
                 actors=draws))
        rooms[room]+=1
        tick_index[tick]+=1
        actor_ids.update(x["id"] for x in draws if room==12)
    if not rooms[7] or not rooms[12]:
        raise ValueError(f"Missing indexed engine frames for either room: {dict(rooms)}")
    extra=set(tick_index).difference(ticks)
    if extra: raise ValueError(f"Unlinked indexed ticks: {sorted(extra)[:10]}")
    known_sdl_ticks=set(x["tick"] for x in presentations)
    matched_sdl_ticks=sum(1 for row in engine_rows if row["tick"] in known_sdl_ticks)
    has_secondary=(actor_ids[7]>0 and actor_ids[8]>0)
    result=dict(schema="scummbucket-cross-room-indexed-evidence/1",
                status="indexed_capture_with_actor7_8_observed" if has_secondary
                       else "partial_indexed_capture_missing_actor7_or_actor8",
                capture=str(capture),indexed_frame_count=len(engine_rows),
                tick_count=len(ticks),sdl_presentations=len(presentations),
                rooms={str(r):n for r,n in sorted(rooms.items())},
                room12_actor_draw_counts={str(a):n for a,n in sorted(actor_ids.items())},
                frames_with_matching_sdl_tick=matched_sdl_ticks,
                # Not claiming actual 1:1 scene snapshots at SDL render phase.
                association="tick_key_only; no exact display-phase or RGB-to-index identity",
                scene_fidelity="NOT VALIDATED",
                missing_indexed_per_tick=sum(1 for t in ticks if t not in tick_index),
                frames=engine_rows,presentations=presentations)
    report.mkdir(exist_ok=True)
    output=report/"cross-room-indexed.json"
    with output.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2)
    if not has_secondary:
        raise ValueError("Cross-room indexed buffers exist but actor 7/8 draw states not both observed")
    return result
