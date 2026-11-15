"""Read-only original DOS VGA SCUMM v5 OBIM indexed-state smoke test.

Usage:
  python -B -m tools.probe_native_object_state --game ORIGINAL_GAME_FOLDER \
      --room 34 --object 358

Reports only source provenance, per-state SHA256, index/opacity counts,
Z plane hashes and diagnostic outcomes. No PNGs, raw assets, engine run,
script execution, state selection, autoplay, input changes or file outputs.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse
import json

from scummbucket.inspector import XOR_KEY, _read_pair, inspect
from scummbucket.native_object_state import decode_indexed_object_state


def probe(game, *, room_id, object_id):
    source=Path(game)
    report=dict(schema="scummbucket-native-object-state-probe/1",
                status="failed", source=str(source),room_id=room_id,
                object_id=object_id,
                evidence="read_only_original_archive_decode",
                runtime_state_observed=False, runtime_animation_verified=False,
                render_fidelity_verified=False,
                states=[],diagnostics=[],
                summary=dict(decoded=0,failed=0,unsupported=0))
    def issue(code, exc):
        report["diagnostics"].append(dict(code=code,message=str(exc)))
    if (type(room_id) is not int or not 0<=room_id<=255 or
        type(object_id) is not int or not 1<=object_id<=65535):
        issue("SELECTION_INVALID","Room or object ID outside original SCUMM v5 bounds")
        return report
    try:
        inventory=inspect(source)
        if inventory["status"]!="success":
            raise ValueError("Archive inspection not successful; inspect its diagnostics separately")
        room,=(r for r in inventory["scene_inventory"]["rooms"] if r["room_id"]==room_id)
        matches=[obj for obj in room["objects"] if obj["object_id"]==object_id]
        if len(matches)!=1 or matches[0]["status"]!="paired" or matches[0]["image"] is None:
            raise ValueError("Room object is absent, ambiguous or unpaired")
        obj=matches[0]
        index,resource,index_label,resource_label=_read_pair(source)
        expected=inventory["sources"]
        if (sha256(index).hexdigest()!=expected[0]["sha256"] or
            sha256(resource).hexdigest()!=expected[1]["sha256"]):
            raise ValueError("Original archive bytes changed between inventory and source reopen")
        decoded=bytes(c^XOR_KEY for c in resource)
        chunks=inventory["resources"]["resource_inventory"]
        in_room=[x for x in chunks if x["room_id"]==room_id]
        trns=[x for x in in_room if x["tag"]=="TRNS"]
        if len(trns)!=1 or trns[0]["length"]<9:
            raise ValueError("Expected one room TRNS chunk with transparency index")
        transparent_index=decoded[trns[0]["offset"]+8]
        image=obj["image"]
        if image["declared_image_count"]!=image["observed_image_count"]:
            raise ValueError("Object image header count inconsistent")
        tags=image["image_state_tags"]
        if not tags:
            raise ValueError("Object has no image-state chunks")
        report["original_archives"]=[
            dict(name=label,size=entry["size"],sha256=entry["sha256"])
            for label,entry in zip((index_label,resource_label),expected)]
        report["object_source"]=dict(
            room_offset=room["room_offset"],room_size=room["room_size"],
            obim_offset=image["source_offset"],obim_length=image["byte_length"],
            state_tags=tags,transparent_index=transparent_index,
            script_state_pattern_count=obj.get("script_state_pattern_count",0),
            script_pattern_instruction_alignment_verified=False,
        )
    except (OSError,ValueError,KeyError,StopIteration) as exc:
        issue("SOURCE_PREFLIGHT_FAILED",exc)
        return report

    for tag in tags:
        row=dict(state_tag=tag,status="failed")
        report["states"].append(row)
        try:
            state=decode_indexed_object_state(
                decoded,obim_offset=image["source_offset"],
                state_tag=tag,transparent_color=transparent_index)
            indices=state["pixels"]
            opacity=state["opacity"]
            row.update(dict(status="indexed_source_decoded_not_runtime_verified",
                source_offset=state["source_offset"],
                source_length=state["source_length"],
                dimensions=[state["width"],state["height"]],
                indexed_sha256=state["indexed_sha256"],
                opacity_sha256=state["opacity_sha256"],
                opaque_pixels=opacity.count(255),
                transparent_pixels=opacity.count(0),
                unique_stored_palette_indices=len(set(indices)),
                strip_codecs=dict(sorted(Counter(
                    str(v["codec"]) for v in state["strip_codecs"]).items())),
                zplanes={
                    tag:dict(sha256=sha256(mask).hexdigest(),
                             set_pixels=mask.count(255))
                    for tag,mask in sorted(state["masks"].items())
                }))
            report["summary"]["decoded"]+=1
        except Exception as exc:
            # State failure must not turn the remaining stored states into
            # falsely verified output, or disappear from the manifest.
            code=getattr(exc,"code","DECODE_FAILED")
            issue(code,f"{tag}: {type(exc).__name__}: {exc}")
            row["failure_code"]=code
            report["summary"]["failed"]+=1
            if code in ("STRIP_CODEC_UNSUPPORTED","IMAGE_DIMENSIONS_UNSUPPORTED",
                        "IMAGE_COUNT_UNSUPPORTED"):
                report["summary"]["unsupported"]+=1
    report["status"]="success" if not report["summary"]["failed"] else (
        "partial" if report["summary"]["decoded"] else "failed")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game",required=True,type=Path)
    parser.add_argument("--room",required=True,type=int)
    parser.add_argument("--object",required=True,type=int)
    args=parser.parse_args()
    result=probe(args.game,room_id=args.room,object_id=args.object)
    print(json.dumps(result,indent=2))
    return 0 if result["status"]=="success" else 2


if __name__=="__main__":
    raise SystemExit(main())
