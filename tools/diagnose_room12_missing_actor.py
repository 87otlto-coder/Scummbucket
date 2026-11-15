"""Forensic, read-only Room 12 residual analysis from the ORIGINAL indexed fronts.

Isolate frames where the drawn-actor trace omits Guybrush and compare their
residual pixels with the source background, immediate adjacent captured
indexed frames, and counterfactual insertion of the nearest *observed*
Guybrush pose. Counterfactuals are hypotheses only: no script interpreter,
no inferred animation state accepted, no modified renderer or capture.

The program reads the original DOS VGA archives and pinned raw engine frames
and their hashes. By default it writes nothing; --output writes exactly one
new, exclusively created private JSON file under FIXTURE if requested.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.scene_source import compose_actor_layers, load_scene
from tools.compare_cross_room_scene import costumes_from_archive
from tools.compare_room23_frames import engine


WIDTH, HEIGHT = 320, 144
PIXELS = WIDTH * HEIGHT


def _load_json(path, maximum=24*1024*1024):
    path=Path(path)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Missing or oversized existing JSON evidence: " + str(path))
    return json.loads(path.read_bytes())


def _raw_front(capture, by_frame, number):
    if number not in by_frame:
        return None
    record=by_frame[number]
    path=Path(capture)/("engine-%03d.bin" % number)
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=record["raw_sha256"]:
        raise ValueError("Changed raw engine capture at frame %d" % number)
    meta,palettes,background,front,_=engine(raw,number)
    if len(front)!=PIXELS or len(background)!=PIXELS:
        raise ValueError("Unexpected indexed framebuffer dimensions")
    if sha256(front).hexdigest()!=record["front_sha256"]:
        raise ValueError("Recorded original front digest mismatch at %d" % number)
    if sha256(background).hexdigest()!=record["background_sha256"]:
        raise ValueError("Recorded original background digest mismatch at %d" % number)
    return background,front


def _residual_categories(background, candidate, original):
    buckets=Counter()
    locations=[]
    for i,(bg,pred,actual) in enumerate(zip(background,candidate,original)):
        if pred==actual:
            continue
        locations.append(i)
        if pred==bg and actual!=bg:
            buckets["observed_foreground_missing_from_candidate"]+=1
        elif pred!=bg and actual==bg:
            buckets["candidate_foreground_not_in_observation"]+=1
        else:
            buckets["different_foreground_indices"]+=1
    return buckets,locations


def _bounds(locations):
    if not locations:return None
    return [
        min(i%WIDTH for i in locations),
        min(i//WIDTH for i in locations),
        1+max(i%WIDTH for i in locations),
        1+max(i//WIDTH for i in locations),
    ]


def diagnose(game,capture,comparison_path,indexed_path):
    game,capture=Path(game),Path(capture)
    comparison=_load_json(comparison_path)
    indexed=_load_json(indexed_path)
    if (comparison.get("schema")!="scummbucket-room12-indexed-multi-actor-probe/1" or
        indexed.get("schema")!="scummbucket-cross-room-indexed-evidence/1" or
        comparison.get("capture")!=indexed.get("capture") or
        str(capture.resolve())!=str(Path(indexed["capture"]).resolve()) or
        indexed.get("status")!="indexed_capture_with_actor7_8_observed" or
        indexed.get("scene_fidelity")!="NOT VALIDATED"):
        raise ValueError("Mismatched prior capture or original indexed-comparison evidence")
    by_frame={}
    for frame in indexed["frames"]:
        n=frame["indexed_frame"]
        if n in by_frame:
            raise ValueError("Duplicate indexed record")
        by_frame[n]=frame
    selected={}
    for frame in comparison["frames"]:
        n=frame["indexed_frame"]
        if n in selected or n not in by_frame:
            raise ValueError("Duplicate/missing compared indexed frame")
        metadata=by_frame[n]
        if (metadata["room"]!=12 or
            metadata["tick"]!=frame["tick"] or
            metadata["front_sha256"]!=frame["engine_indexed_sha256"] or
            [a["id"] for a in metadata["actors"]]!=frame["draw_order"]):
            raise ValueError("Comparison/source frame linkage differs")
        selected[n]=frame
    if len(selected)!=comparison.get("samples"):
        raise ValueError("Original comparison sample count differs")
    if sum(r["indexed_errors"] for r in selected.values())!=comparison.get("unexplained_mismatches"):
        raise ValueError("Original comparison residual total differs")
    problem=[n for n,row in selected.items() if row["indexed_errors"]]
    if not problem:
        return dict(schema="scummbucket-room12-actor-absence-forensics/1",
                    status="no_residuals_to_diagnose",frames_examined=0)
    if any(any(a["id"]==1 for a in by_frame[n]["actors"]) for n in problem):
        raise ValueError("Residuals are not exclusively in frames omitting actor 1; reassess hypothesis")
    scene=load_scene(game,12)
    if scene["manifest"]["dimensions"]!=[WIDTH,HEIGHT]:
        raise ValueError("Unexpected source room size")
    if scene["manifest"]["room_sha256"]!=comparison["source_room_sha256"]:
        raise ValueError("Original source room differs from comparison")
    needed={a["costume"] for row in by_frame.values() if row["room"]==12
            for a in row["actors"]}
    costumes=costumes_from_archive(game,needed)
    known1=sorted(
        (n,row["actors"][i])
        for n,row in by_frame.items() if row["room"]==12
        for i,a in enumerate(row["actors"]) if a["id"]==1
    )
    if not known1:
        raise ValueError("No recorded Guybrush pose for counterfactual")
    details=[]
    totals=Counter()
    hypothetical=Counter()
    for number in sorted(problem):
        row=by_frame[number]
        recorded=selected[number]
        background,observed=_raw_front(capture,by_frame,number)
        if background!=scene["background"]:
            raise ValueError("Recorded background differs from original indexed scene at %d" % number)
        predicted=compose_actor_layers(scene,costumes,row["actors"])
        if sha256(predicted).hexdigest()!=recorded["predicted_indexed_sha256"]:
            raise ValueError("Current compositor no longer reproduces original saved comparison at %d" % number)
        buckets,locations=_residual_categories(background,predicted,observed)
        if len(locations)!=recorded["indexed_errors"] or _bounds(locations)!=recorded["bbox"]:
            raise ValueError("Actual indexed residual pixels disagree with original report at %d" % number)
        totals.update(buckets)
        preceding=[(n,a) for n,a in known1 if n<number]
        following=[(n,a) for n,a in known1 if n>number]
        neighbors={}
        for key,offset in (("previous",-1),("following",1)):
            existing=_raw_front(capture,by_frame,number+offset)
            if existing:
                _,neighbor=existing
                neighbors[key]=dict(frame=number+offset,
                    observed_matches_at_residual_positions=sum(
                        observed[i]==neighbor[i] for i in locations),
                    frame_pixels_differ_from_current=sum(a!=b for a,b in zip(observed,neighbor)))
        variants={}
        for label,source in (("last_observed",preceding[-1] if preceding else None),
                             ("next_observed",following[0] if following else None)):
            if source is None:
                continue
            original_frame,guybrush=source
            candidates={}
            for insertion,position in (("before_other_actors",0),
                                        ("between_actor7_and_actor8",1),
                                        ("after_other_actors",len(row["actors"]))):
                ordered=list(row["actors"])
                ordered.insert(position,guybrush)
                test=compose_actor_layers(scene,costumes,ordered)
                errors=sum(p!=o for p,o in zip(test,observed))
                candidates[insertion]=dict(errors=errors,
                    delta_vs_baseline=recorded["indexed_errors"]-errors)
                hypothetical[label+"."+insertion]+=errors
            variants[label]=dict(original_observed_frame=original_frame,
                                 state=dict(position=[guybrush["screen_x"],guybrush["draw_y"]],
                                            facing=guybrush["facing"],
                                            plane=guybrush["plane"],
                                            scale=guybrush["scales"],
                                            frame=guybrush["logical_frame"],
                                            stopped=guybrush["stopped"],
                                            cursors=guybrush["cursors"]),
                                 candidate_errors=candidates)
        details.append(dict(frame=number,tick=row["tick"],
            original_indexed_errors=len(locations),
            actual_bbox=_bounds(locations),
            categories=dict(buckets),
            adjacent_recorded_front=neighbors,
            nearest_recorded_actor1_counterfactuals=variants))
    if sum(totals.values())!=comparison["unexplained_mismatches"]:
        raise ValueError("Residual categories do not reconcile")
    return dict(schema="scummbucket-room12-actor-absence-forensics/1",
        status="counterfactual_diagnostics_only_not_a_rendering_acceptance",
        original_comparison_status=comparison["status"],
        capture=str(capture),
        original_room_sha256=scene["manifest"]["room_sha256"],
        problem_frames=len(details),
        previous_exact_frames=204 if False else None,
        original_residual_pixels=sum(totals.values()),
        residual_categories=dict(totals),
        hypothetical_aggregate_errors=dict(hypothetical),
        counterfactual_semantics="Insert only previously observed actor1 state; not evidence it was actually drawn",
        interpretation_warning="Cache, missing draw trace and additional object layer remain hypotheses; observed full-scene indexed equality unproven",
        frames=details)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game",type=Path,required=True)
    p.add_argument("--capture",type=Path,required=True)
    p.add_argument("--comparison",type=Path,required=True)
    p.add_argument("--indexed",type=Path,required=True)
    p.add_argument("--output",type=Path,
                   help="Optional private fresh JSON filepath, exclusive creation only")
    args=p.parse_args()
    report=diagnose(args.game,args.capture,args.comparison,args.indexed)
    text=json.dumps(report,indent=2)
    if args.output is not None:
        with args.output.open("x",encoding="utf-8") as destination:
            destination.write(text)
    print(text)


if __name__=="__main__":
    main()
