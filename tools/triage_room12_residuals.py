"""Read-only Room 12 per-frame residual triage using existing private JSON.

This tool does NOT re-run ScummVM, decode original resources, infer actor
timing, edit any report, or claim new pixel fidelity. It joins the already
generated source-vs-engine comparison and the accepted indexed actor
metadata by exact original indexed frame and tick IDs. Grouping can
identify useful next hypotheses, not prove which actor caused an error.
"""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import statistics


def _count(row, key):
    value=row.get(key)
    if type(value) is not int or not 0 <= value <= 46080:
        raise ValueError(f"Invalid per-frame {key}: {value!r}")
    return value


def _group(items, key, *, limit=12):
    groups=defaultdict(list)
    for item in items:
        groups[key(item)].append(item)
    rows=[]
    for label, members in groups.items():
        errors=[m["indexed_errors"] for m in members]
        rows.append(dict(key=label,frames=len(members),errors=sum(errors),
                         mean_errors=round(statistics.mean(errors),2),
                         exact_frames=errors.count(0),
                         first_tick=min(m["tick"] for m in members),
                         last_tick=max(m["tick"] for m in members)))
    rows.sort(key=lambda r:(-r["errors"],-r["frames"],r["key"]))
    return rows[:limit],len(rows)


def _active_state(actor):
    if actor is None:
        return "not-drawn"
    cursors=actor["cursors"]
    stopped=actor["stopped"]
    if len(cursors)!=16 or type(stopped) is not int:
        raise ValueError("Incomplete observed actor state")
    visible=[[i,n] for i,n in enumerate(cursors)
             if n!=65535 and not (stopped&(1<<i))]
    return json.dumps(dict(frame=actor["logical_frame"],facing=actor["facing"],
                           stopped=stopped,cursors=visible),separators=(",",":"))


def _runs(items):
    runs=[]
    current=None
    for item in items:
        if item["indexed_errors"]==0:
            if current is not None:
                runs.append(current)
                current=None
            continue
        if current is None:
            current=dict(start_tick=item["tick"],end_tick=item["tick"],
                         frames=1,errors=item["indexed_errors"])
        elif item["tick"]==current["end_tick"]+1:
            current["end_tick"]=item["tick"]
            current["frames"]+=1
            current["errors"]+=item["indexed_errors"]
        else:
            runs.append(current)
            current=dict(start_tick=item["tick"],end_tick=item["tick"],
                         frames=1,errors=item["indexed_errors"])
    if current is not None:
        runs.append(current)
    runs.sort(key=lambda r:(-r["errors"],r["start_tick"]))
    return runs[:15],len(runs)


def summarize(comparison, indexed):
    if (comparison.get("schema")!="scummbucket-room12-indexed-multi-actor-probe/1" or
        indexed.get("schema")!="scummbucket-cross-room-indexed-evidence/1" or
        indexed.get("status")!="indexed_capture_with_actor7_8_observed" or
        indexed.get("scene_fidelity")!="NOT VALIDATED" or
        comparison.get("capture")!=indexed.get("capture")):
        raise ValueError("Comparison/indexed report provenance or schema mismatch")
    source=[row for row in indexed["frames"] if row["room"]==12]
    if not source:
        raise ValueError("No source Room 12 records")
    keyed={}
    for row in source:
        frame=row["indexed_frame"]
        if frame in keyed or type(frame) is not int:
            raise ValueError("Duplicate or invalid source indexed frame")
        keyed[frame]=row
    items=[]
    seen=set()
    for entry in comparison["frames"]:
        frame=entry["indexed_frame"]
        if frame in seen or frame not in keyed:
            raise ValueError(f"Duplicate or unknown comparison frame {frame}")
        seen.add(frame)
        original=keyed[frame]
        if (entry.get("tick")!=original["tick"] or
            entry.get("engine_indexed_sha256")!=original["front_sha256"] or
            entry.get("draw_order")!=[a["id"] for a in original["actors"]]):
            raise ValueError(f"Original source tick/front hash/draw order mismatch at frame {frame}")
        counts={key:_count(entry,key) for key in
                ("indexed_errors","mask_disabled_errors",
                 "source_background_errors","mask_changed_pixels")}
        actors={a["id"]:a for a in original["actors"]}
        items.append(dict(tick=original["tick"],indexed_frame=frame,
            draw_order="-".join(str(a["id"]) for a in original["actors"]),
            actor1_present=1 in actors,actors=actors,
            bbox=entry.get("bbox"),first_mismatch=entry.get("first_mismatch"),
            **counts))
    if set(keyed)!=seen:
        raise ValueError(f"Missing {len(set(keyed)-seen)} Room 12 comparison frames")
    items.sort(key=lambda r:r["tick"])
    if any(b["tick"]!=a["tick"]+1 for a,b in zip(items,items[1:])):
        raise ValueError("Room 12 tick sequence is not consecutive")
    sums={name:sum(item[name] for item in items) for name in
          ("indexed_errors","mask_disabled_errors",
           "source_background_errors","mask_changed_pixels")}
    expected={
        "indexed_errors":"indexed_mismatches",
        "mask_disabled_errors":"unmasked_mismatches",
        "source_background_errors":"source_background_mismatches",
        "mask_changed_pixels":"pixels_modified_by_mask"
    }
    for local,source_name in expected.items():
        if sums[local]!=comparison["totals"].get(source_name):
            raise ValueError(f"Comparison aggregate does not match {source_name}")
    if comparison.get("samples")!=len(items) or comparison.get("indexed_pixel_observations")!=len(items)*46080:
        raise ValueError("Reported sample/viewport count is inconsistent")
    if sums["indexed_errors"]!=comparison.get("unexplained_mismatches"):
        raise ValueError("Unexplained residual count inconsistent")
    errors=sorted(x["indexed_errors"] for x in items)
    exact=sum(x==0 for x in errors)
    worst=sorted(items,key=lambda x:(-x["indexed_errors"],x["tick"]))[:20]
    worst=[{k:v for k,v in item.items() if k!="actors"} for item in worst]
    order,n_order=_group(items,lambda x:x["draw_order"])
    guybrush,n_guybrush=_group(items,lambda x:_active_state(x["actors"].get(1)))
    actor7,n_actor7=_group(items,lambda x:_active_state(x["actors"].get(7)))
    actor8,n_actor8=_group(items,lambda x:_active_state(x["actors"].get(8)))
    present,n_present=_group(items,lambda x:"present" if x["actor1_present"] else "not-drawn")
    runs,n_runs=_runs(items)
    corrected=sums["mask_disabled_errors"]-sums["indexed_errors"]
    return dict(schema="scummbucket-room12-residual-triage/1",
        status="derived_metadata_diagnostics_not_scene_acceptance",
        evidence="Join of two previous private JSON reports, no raw pixels reread",
        frames=len(items),exact_frames=exact,frames_with_errors=len(items)-exact,
        residual_pixels=sums["indexed_errors"],
        mean_residuals_per_frame=round(statistics.mean(errors),3),
        median_residuals_per_frame=statistics.median(errors),
        p90_residuals_per_frame=errors[(len(errors)*9+9)//10-1],
        worst_frame_errors=max(errors),
        matched_index_positions=len(items)*46080-sums["indexed_errors"],
        total_index_positions=len(items)*46080,
        background_disagreements=sums["source_background_errors"],
        unmasked_errors=sums["mask_disabled_errors"],
        mask_changed_pixels=sums["mask_changed_pixels"],
        masked_errors_eliminated=corrected,
        all_mask_changes_reduce_errors=(corrected==sums["mask_changed_pixels"]),
        error_runs_count=n_runs,largest_error_runs=runs,
        worst_frames=worst,
        draw_order_groups=order,draw_order_group_count=n_order,
        guybrush_presence_groups=present,
        actor1_state_groups=guybrush,actor1_state_count=n_guybrush,
        actor7_state_groups=actor7,actor7_state_count=n_actor7,
        actor8_state_groups=actor8,actor8_state_count=n_actor8,
        interpretation_warning="Correlations do not establish causal actor, phase, palette, or object faults")


def read_and_summarize(comparison_path,indexed_path):
    cbytes=Path(comparison_path).read_bytes()
    ibytes=Path(indexed_path).read_bytes()
    result=summarize(json.loads(cbytes),json.loads(ibytes))
    result["comparison_json_sha256"]=sha256(cbytes).hexdigest()
    result["indexed_json_sha256"]=sha256(ibytes).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison",type=Path,required=True)
    parser.add_argument("--indexed",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(read_and_summarize(args.comparison,args.indexed),indent=2))


if __name__=="__main__":
    main()
