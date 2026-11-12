"""Reproducible, selective SCUMM chunk export with explicit per-item outcomes.

Exports *uninterpreted SCUMM chunks* including their eight-byte chunk headers.
'Decoded' here means removal of the file-level XOR 0x69 obfuscation ONLY:
it does not mean graphic, audio, or script resource decoding.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path

from .inspector import XOR_KEY, _read_pair, inspect, InspectionError
from .linking import TYPE_TAGS


def _diag(code: str, message: str, *, source: str | None = None, offset: int | None = None,
          resource_id: int | None = None, tag: str | None = None,
          severity: str = "error") -> dict:
    return {"severity": severity, "code": code, "message": message, "source": source,
            "offset": offset, "resource_id": resource_id, "tag": tag}


def _write_new_verified(path: Path, contents: bytes) -> str:
    """Exclusive creation; no overwrite, even of a symlink. Verify written hash."""
    expected = sha256(contents).hexdigest()
    created = False
    try:
        with path.open("xb") as stream:
            created = True
            stream.write(contents)
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise OSError("Checksum mismatch after write")
        return actual
    except OSError:
        if created:
            try:
                path.unlink()
            except OSError as cleanup_exc:
                raise OSError(f"Incomplete file cleanup failed ({cleanup_exc}); inspect {path}") from cleanup_exc
        raise


def extract(input_path: str | Path, output_dir: str | Path, *, room_id: int | None = None,
            tag: str | None = None, directory: str | None = None,
            resource_id: int | None = None, representation: str = "decoded") -> dict:
    """Export selected room chunks OR one validated index-directory resource.

    Original game archives are never written; all exported chunks retain
    their SCUMM header. A resource ID always resolves to one exact chunk,
    never all chunks of its type in the same room.
    """
    src_path, dest = Path(input_path), Path(output_dir)
    by_id = directory is not None or resource_id is not None
    report: dict = {"schema_version": "0.1", "operation": "extract_index_id" if by_id else "extract_chunks",
                    "status": "failed", "input": str(src_path), "output_dir": str(dest),
                    "selection": {"room_id": room_id, "tag": tag, "directory": directory,
                                  "resource_id": resource_id, "representation": representation},
                    "sources": [], "items": [], "summary": {s: 0 for s in
                    ("success", "failed", "skipped", "unsupported")}, "diagnostics": []}
    errors = report["diagnostics"]

    if by_id:
        if room_id is not None or tag is not None:
            errors.append(_diag("SELECTION_CONFLICT", "Choose either room/tag or directory/resource ID"))
            return report
        if directory not in TYPE_TAGS:
            errors.append(_diag("DIRECTORY_TYPE_UNSUPPORTED", f"Unsupported index directory {directory!r}"))
            report["summary"]["unsupported"] += 1
            return report
        if type(resource_id) is not int or resource_id < 0:
            errors.append(_diag("RESOURCE_ID_INVALID", "Resource ID must be a nonnegative integer"))
            return report
    else:
        if type(room_id) is not int or not 0 <= room_id <= 255:
            errors.append(_diag("SELECTION_ROOM_INVALID", "Room ID must be in 0..255"))
            return report
        if tag is not None and (len(tag) != 4 or not tag.isascii() or not tag.isalnum() or tag != tag.upper()):
            errors.append(_diag("SELECTION_TAG_INVALID", "Tag must be four uppercase alphanumeric characters"))
            return report
    if representation not in ("decoded", "stored"):
        errors.append(_diag("REPRESENTATION_UNSUPPORTED", "Expected 'decoded' or 'stored'"))
        report["summary"]["unsupported"] += 1
        return report

    inventory = inspect(src_path)
    report["sources"] = inventory["sources"]
    errors.extend(inventory["diagnostics"])
    if inventory["status"] != "success":
        errors.append(_diag("EXTRACT_INSPECTION_FAILED", "Source archive did not pass structural inspection"))
        return report

    if by_id:
        directory_info = inventory["index"].get(directory)
        if directory_info is None or resource_id >= directory_info.get("slots", 0):
            errors.append(_diag("RESOURCE_ID_OUT_OF_RANGE",
                                f"{directory}[{resource_id}] is not a valid directory slot"))
            return report
        links = [r for r in inventory["directory_links"]["entries"]
                 if r["directory"] == directory and r["id"] == resource_id]
        if len(links) != 1:
            errors.append(_diag("RESOURCE_ID_LINK_MISSING",
                                f"No unique directory link for {directory}[{resource_id}]"))
            return report
        link = links[0]
        if link["status"] == "unused":
            report["summary"]["skipped"] += 1
            errors.append(_diag("RESOURCE_SLOT_UNUSED",
                                f"{directory}[{resource_id}] is an unused directory slot",
                                resource_id=resource_id, tag=TYPE_TAGS[directory]))
            return report
        if link["status"] != "linked":
            errors.append(_diag("RESOURCE_LINK_UNRESOLVED",
                                f"{directory}[{resource_id}] failed structural validation",
                                resource_id=resource_id, tag=TYPE_TAGS[directory]))
            return report
        selected = [{"room_id": link["room_id"], "tag": link["expected_tag"],
                     "scope": "indexed", "offset": link["source_offset"],
                     "length": link["byte_length"], "directory": directory,
                     "resource_id": resource_id}]
    else:
        selected = [r for r in inventory["resources"]["resource_inventory"]
                    if r["room_id"] == room_id and (tag is None or r["tag"] == tag)]
        if not selected:
            errors.append(_diag("EXTRACT_NO_MATCHES", f"No inventory resources match room={room_id}, tag={tag}"))
            return report

    # No user-provided path fragments are used in output basenames.
    if dest.is_symlink():
        errors.append(_diag("OUTPUT_DIRECTORY_SYMLINK", "Refusing a symlink as output directory", source=str(dest)))
        return report
    try:
        dest.mkdir(parents=True, exist_ok=True)
        if not dest.is_dir():
            raise NotADirectoryError(str(dest))
    except OSError as exc:
        errors.append(_diag("OUTPUT_DIRECTORY_FAILED", f"Cannot create output directory: {exc}", source=str(dest)))
        return report

    manifest = dest / "manifest.json"
    if manifest.exists() or manifest.is_symlink():
        errors.append(_diag("MANIFEST_EXISTS", "manifest.json exists; refusing to overwrite or add unlabeled outputs",
                            source=str(manifest)))
        return report

    try:
        index_bytes, resource_bytes, index_label, resource_label = _read_pair(src_path)
    except (InspectionError, OSError) as exc:
        errors.append(_diag("EXTRACT_REOPEN_FAILED", f"Cannot reopen source: {exc}", source=str(src_path)))
        return report
    index_hash = sha256(index_bytes).hexdigest()
    if index_hash != inventory["sources"][0]["sha256"]:
        errors.append(_diag("EXTRACT_INPUT_CHANGED",
                            "Index file changed after inventory; extraction blocked",
                            source=index_label))
        return report
    resource_hash = sha256(resource_bytes).hexdigest()
    if resource_hash != inventory["sources"][1]["sha256"]:
        errors.append(_diag("EXTRACT_INPUT_CHANGED",
                            "Resource file changed after inventory; extraction blocked",
                            source=resource_label))
        return report

    for entry in sorted(selected, key=lambda x: (x["offset"], x["tag"])):
        offset, length, kind = entry["offset"], entry["length"], entry["tag"]
        if by_id:
            filename = (f"{directory}-{resource_id:04d}_room-{entry['room_id']:03d}_"
                        f"{kind}_0x{offset:08X}.{representation}.bin")
        else:
            filename = f"room-{room_id:03d}_{kind}_0x{offset:08X}.{representation}.bin"
        location = dest / filename
        item = {"room_id": entry["room_id"], "tag": kind, "scope": entry["scope"],
                "directory": entry.get("directory"), "resource_id": entry.get("resource_id"),
                "source": resource_label, "source_sha256": resource_hash,
                "source_offset": offset, "byte_length": length,
                "representation": representation, "file": filename,
                "status": "failed", "sha256": None}
        report["items"].append(item)
        if offset < 0 or length < 8 or offset + length > len(resource_bytes):
            errors.append(_diag("EXTRACT_RANGE_INVALID", "Chunk range falls outside input", source=resource_label,
                                offset=offset, resource_id=entry.get("resource_id", room_id), tag=kind))
            continue
        stored = resource_bytes[offset:offset + length]
        contents = bytes(x ^ XOR_KEY for x in stored) if representation == "decoded" else stored
        item["source_slice_sha256"] = sha256(stored).hexdigest()
        item["decoded_chunk_sha256"] = sha256(bytes(x ^ XOR_KEY for x in stored)).hexdigest()
        try:
            item["sha256"] = _write_new_verified(location, contents)
            item["status"] = "success"
        except OSError as exc:
            errors.append(_diag("EXTRACT_WRITE_FAILED", f"Could not write {filename}: {exc}",
                                source=str(location), offset=offset,
                                resource_id=entry.get("resource_id", room_id), tag=kind))

    report["summary"].update(Counter(r["status"] for r in report["items"]))
    success, failed = report["summary"]["success"], report["summary"]["failed"]
    report["status"] = "success" if success and not failed else "partial" if success else "failed"
    # Always produce a manifest when possible, even for partial success.
    try:
        _write_new_verified(manifest, (json.dumps(report, indent=2) + "\n").encode("utf-8"))
    except OSError as exc:
        errors.append(_diag("MANIFEST_WRITE_FAILED", f"Could not write manifest: {exc}", source=str(manifest)))
        report["status"] = "partial" if success else "failed"
    return report
