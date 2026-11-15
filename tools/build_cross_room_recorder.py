"""Build P4 cross-room research instrumentation in a fresh TOOLS copy.

Never modify the pinned ScummVM doorway source or executable. The original
doorway build is fingerprinted before any output is created. Each attempt
uses new UUID paths and records its outcome. An existing copied executable
is never reported as a successful new build without a changed digest.
This is Windows-private tooling, not a CI distribution/build artifact.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from tools.instrument_room7_doorway import BUILD as DOORWAY_BUILD
from tools.prepare_cross_room_capture import prepare


SOURCE_FILES = ("engines/scumm/scumm.cpp", "engines/scumm/actor.cpp")
MAKE = Path("C:/msys64/usr/bin/make.exe")
RUNTIME_DLLS = Path("C:/msys64/ucrt64/bin")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def preflight(root, *, make=MAKE, dlls=RUNTIME_DLLS):
    root=Path(root).resolve()
    if any(not (root/name).is_dir() for name in ("SOURCE","TOOLS","FIXTURE")):
        raise ValueError("Root must use existing SOURCE, TOOLS, FIXTURE directories")
    source=root/"TOOLS"/DOORWAY_BUILD
    exe=source/"scummvm.exe"
    marker=source/"doorway-exe.sha256"
    if not exe.is_file() or not marker.is_file():
        raise ValueError("Pinned doorway executable or fingerprint missing")
    expected=marker.read_text(encoding="utf-8").strip().lower()
    if not expected or digest(exe)!=expected:
        raise ValueError("Pinned doorway executable digest mismatch")
    if not make.is_file() or not dlls.is_dir():
        raise ValueError("Pinned Windows MSYS2 compiler or DLL directory missing")
    # read-only source check. The subsequent prepare() repeats its own hashes.
    for name in SOURCE_FILES:
        if not (source/name).is_file():
            raise ValueError(f"Missing pinned doorway source: {name}")
    return dict(root=str(root), source=str(source),
                source_exe_sha256=digest(exe), make=str(make),
                dlls=str(dlls))


def build(root, *, make=MAKE, dlls=RUNTIME_DLLS):
    info=preflight(root,make=make,dlls=dlls)
    src=Path(info["source"])
    tools=Path(info["root"])/"TOOLS"
    ident=uuid4().hex
    overlay=tools/("P5-CrossRoom-Overlay-"+ident)
    target=tools/("ScummVM-P4-CrossRoom-"+ident)
    if overlay.exists() or target.exists():
        raise FileExistsError("Fresh private TOOLS build destination already exists")
    # prepare() verifies both pinned original source SHA-256 hashes.
    source_overlay=prepare(src,overlay)
    if len(source_overlay["files"])!=len(SOURCE_FILES):
        raise ValueError("Missing instrumented source file in P5 overlay")
    # No existing files in the original build are touched.
    shutil.copytree(src,target,ignore=shutil.ignore_patterns(".git"))
    for entry in source_overlay["files"]:
        rel=Path(entry["path"])
        if rel.as_posix() not in SOURCE_FILES:
            raise ValueError("Unexpected cross-room overlay path")
        old=target/rel
        if digest(old)!=entry["input_sha256"]:
            raise ValueError(f"Changed copied source: {rel}")
        payload=(overlay/rel).read_bytes()
        if sha256(payload).hexdigest()!=entry["output_sha256"]:
            raise ValueError(f"Overlay digest mismatch: {rel}")
        old.write_bytes(payload)  # only inside newly copied TOOLS tree
    log=target/"cross-room-build.log"
    env=os.environ.copy()
    env["PATH"]=str(dlls)+os.pathsep+str(make.parent)+os.pathsep+env.get("PATH","")
    with log.open("xb") as output:
        subprocess.run([str(make),"-j4"],cwd=target,env=env,
                       stdout=output,stderr=subprocess.STDOUT,check=True)
    linked=target/"scummvm.exe"
    new_hash=digest(linked)
    if new_hash==info["source_exe_sha256"]:
        raise ValueError("Executable unchanged after make: cross-room build is NOT validated")
    version=subprocess.check_output([str(linked),"--version"],cwd=target,env=env,
                                    text=True,errors="replace").strip()
    if not version:
        raise ValueError("New cross-room executable failed version probe")
    result=dict(schema="scummbucket-cross-room-build/1",
                status="linked_executable_version_checked_not_runtime_capture",
                original_doorway_dir=str(src),
                original_doorway_exe_sha256=info["source_exe_sha256"],
                build_dir=str(target), overlay_dir=str(overlay),
                patched_sources=source_overlay["files"],
                exe_sha256=new_hash,version=version,
                build_log=str(log),
                capture_runtime_verified=False)
    # Only a freshly linked build gets this acceptance marker.
    with (target/"cross-room-exe.sha256").open("x",encoding="ascii") as out:
        out.write(new_hash+"\n")
    with (target/"cross-room-build.json").open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--check-only",action="store_true",
                        help="Read-only preflight; do not copy or build")
    args=parser.parse_args()
    print(json.dumps(preflight(args.root) if args.check_only else build(args.root),indent=2))


if __name__=="__main__":
    main()
