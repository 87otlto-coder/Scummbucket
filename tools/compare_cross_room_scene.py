"""Compare an original Room 12 multi-actor composition with indexed engine front.

No fitted palette, synthetic actor timing or RGB inversion. Every pose is an
ordered, engine-observed draw_actor record from the fresh cross-room capture.
Comparison failures remain visible in a new private report. This tool is NOT
a general SCUMM room interpreter or a proof for other routes.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import argparse
import json
from pathlib import Path

from PIL import Image

from scummbucket.classic_costume import ClassicCostume
from scummbucket.inspector import XOR_KEY, _read_pair, inspect
from scummbucket.scene_source import compose_actor_layers, load_scene
from tools.compare_room23_frames import engine


def digest(value):
    return sha256(value).hexdigest()


def costumes_from_archive(game, needed):
    inv=inspect(game)
    if inv.get("status")!="success":
        raise ValueError("Original DOS VGA archive inspection failed")
    links=inv["directory_links"]["entries"]
    _,resources,_,_=_read_pair(game)
    result={}
    for number in sorted(needed):
        matches=[row for row in links if row["directory"]=="DCOS" and row["id"]==number]
        if len(matches)!=1:
            raise ValueError(f"Unresolved original COST resource {number}")
        row=matches[0]
        offset,length=row["source_offset"],row["byte_length"]
        chunk=bytes(byte^XOR_KEY for byte in resources[offset:offset+length])
        result[number]=ClassicCostume(chunk)
    return result


def bbox(mismatches,width):
    if not mismatches:return None
    xs=[n%width for n in mismatches]
    ys=[n//width for n in mismatches]
    return [min(xs),min(ys),max(xs)+1,max(ys)+1]


def compare(game,capture,destination):
    game,capture,destination=Path(game),Path(capture),Path(destination)
    metadata=json.loads((capture/"run.json").read_text(encoding="utf-8"))
    if metadata.get("capture_mode")!="cross_room":
        raise ValueError("Source capture is not a tagged cross-room indexed run")
    capture_report=capture.parent.parent.parent/"REPORTS"/"Room7"/capture.name/"cross-room-indexed.json"
    # Existing filesystem layout root/FIXTURE/CAPTURES/Room7/<id> -> root/FIXTURE/REPORTS/Room7/<id>
    if not capture_report.is_file():
        fixture=capture.parents[2]
        capture_report=fixture/"REPORTS"/"Room7"/capture.name/"cross-room-indexed.json"
    previous=json.loads(capture_report.read_text(encoding="utf-8"))
    if (previous.get("status")!="indexed_capture_with_actor7_8_observed" or
        previous.get("scene_fidelity")!="NOT VALIDATED"):
        raise ValueError("Missing independently validated indexed actor draw capture")
    frames=[row for row in previous["frames"] if row["room"]==12]
    if not frames:
        raise ValueError("No indexed Room 12 frame exists")
    game=game.resolve()
    scene=load_scene(game,12)
    if scene["manifest"]["dimensions"]!=[320,144]:
        raise ValueError("Unexpected original Room 12 source dimensions")
    costumes=costumes_from_archive(game,{a["costume"] for row in frames for a in row["actors"]})
    destination.mkdir(parents=True,exist_ok=False)
    findings=[]
    totals=Counter()
    for row in frames:
        number=row["indexed_frame"]
        source=capture/f"engine-{number:03}.bin"
        raw=source.read_bytes()
        if digest(raw)!=row["raw_sha256"]:
            raise ValueError(f"Indexed Room 12 source changed at frame {number}")
        meta,palettes,recorded_background,observed,_=engine(raw,number)
        if digest(observed)!=row["front_sha256"]:
            raise ValueError(f"Indexed Room 12 front hash changed at frame {number}")
        camera=[0,0,320,144]
        predicted=compose_actor_layers(scene,costumes,row["actors"],camera)
        without_mask=compose_actor_layers(scene,costumes,row["actors"],camera,mask_enabled=False)
        indices=[i for i,(a,b) in enumerate(zip(predicted,observed)) if a!=b]
        altered=[i for i,(a,b) in enumerate(zip(without_mask,observed)) if a!=b]
        bg_diff=sum(a!=b for a,b in zip(scene["background"],recorded_background))
        changed_from_mask=sum(a!=b for a,b in zip(without_mask,predicted))
        totals.update(indexed_mismatches=len(indices),unmasked_mismatches=len(altered),
                      source_background_mismatches=bg_diff,
                      pixels_modified_by_mask=changed_from_mask)
        findings.append(dict(indexed_frame=number,tick=row["tick"],
                             draw_order=[a["id"] for a in row["actors"]],
                             indexed_errors=len(indices),first_mismatch=None if not indices else
                             [indices[0]%320,indices[0]//320],
                             bbox=bbox(indices,320),
                             mask_disabled_errors=len(altered),
                             source_background_errors=bg_diff,
                             mask_changed_pixels=changed_from_mask,
                             predicted_indexed_sha256=digest(predicted),
                             engine_indexed_sha256=digest(observed),
                             engine_final_palette_sha256=digest(palettes[3])))
        if len(findings)==1:
            for filename,pixels in (
                ("candidate.png",predicted),("engine-reference.png",observed)):
                im=Image.frombytes("P",(320,144),pixels)
                im.putpalette(palettes[3])
                with (destination/filename).open("xb") as handle:
                    im.save(handle,format="PNG")
            mask=bytes(255 if x in set(indices) else 0 for x in range(46080))
            with (destination/"indexed-differences.png").open("xb") as output:
                Image.frombytes("L",(320,144),mask).save(output,format="PNG")
    all_exact=totals["indexed_mismatches"]==0 and len(findings)>0
    result=dict(schema="scummbucket-room12-indexed-multi-actor-probe/1",
                status="recorded_route_exact_indexed_match" if all_exact
                       else "PARTIAL_INDEXED_RECONSTRUCTION",
                source_evidence="original archive + captured ordered actor draw state",
                runtime_reference="actual indexed front buffers; not RGB inversion",
                capture=str(capture),game_archive_sources=scene["manifest"]["sources"],
                source_room_sha256=scene["manifest"]["room_sha256"],
                samples=len(findings),indexed_pixel_observations=len(findings)*46080,
                totals=dict(totals),frames=findings,
                unexplained_mismatches=totals["indexed_mismatches"],
                unsupported=[
                   "Unknown object image visibility/state not inferred",
                   "Inter-tick animation updates not synthesized",
                   "SDL final presentation phase not independently synchronized",
                   "No automatic all-room generalization",
                ])
    with (destination/"room12-indexed-compare.json").open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game",type=Path,required=True)
    parser.add_argument("--capture",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.game,args.capture,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!="frames"},indent=2))
    return 0 if result["status"]=="recorded_route_exact_indexed_match" else 2


if __name__=="__main__":
    raise SystemExit(main())
