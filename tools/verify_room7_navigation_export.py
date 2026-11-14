"""Read-only integrity audit of native Room 7 exterior animation exports.

Checks actual indexed pixels, actual PNG palette, encoded file bytes and
segment timeline against animation.json; does NOT claim raw engine comparison.
The independent compositor comparison is the prerequisite export gate.
"""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image


NAME = re.compile(r"frame-[0-9]{4}\.png\Z")


def digest(data):
    return sha256(data).hexdigest()


def verify_export(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "room7-navigation-native-export/1":
        raise ValueError("Unexpected native export schema")
    if (manifest.get("room_id"), manifest.get("geometry")) != (7, [320, 144]):
        raise ValueError("Incorrect Room 7 export geometry")
    if not manifest.get("all_indexed_comparisons_exact") or manifest.get("room12_frames_included") is not False:
        raise ValueError("Manifest does not declare verified exterior-only reconstruction")
    sections = manifest.get("segments")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Missing continuous exterior segments")
    expected_frame = 1
    previous_tick = None
    previous_ms = None
    segment_meta = []
    expected_names = set()
    for section_id, section in enumerate(sections, 1):
        entries = section.get("frames")
        if not isinstance(entries, list) or not entries or section.get("segment") != section_id:
            raise ValueError(f"Invalid segment {section_id}")
        if section.get("first_frame") != expected_frame:
            raise ValueError(f"Non-contiguous manifest frame sequence at segment {section_id}")
        first_tick, last_tick = section.get("first_tick"), section.get("last_tick")
        if type(first_tick) is not int or type(last_tick) is not int:
            raise ValueError(f"Invalid segment ticks at {section_id}")
        if last_tick - first_tick != len(entries) - 1 or (
            section.get("last_frame") != expected_frame + len(entries) - 1
        ):
            raise ValueError(f"Invalid tick/frame range at segment {section_id}")
        gap = None if previous_tick is None else first_tick - previous_tick - 1
        if (previous_tick is not None and gap <= 0) or section.get("omitted_ticks_before") != gap:
            raise ValueError(f"Missing or fabricated segment gap at {section_id}")
        ms_start, ms_end = section.get("first_presentation_ms"), section.get("last_presentation_ms")
        if type(ms_start) is not int or type(ms_end) is not int or ms_end < ms_start:
            raise ValueError(f"Invalid segment presentation bounds at {section_id}")
        if previous_ms is not None and ms_start < previous_ms:
            raise ValueError(f"Nonmonotonic segment presentation start at {section_id}")
        for record in entries:
            frame = record.get("frame")
            name = record.get("file")
            if frame != expected_frame or not isinstance(name, str) or name != f"frame-{expected_frame:04d}.png" or not NAME.fullmatch(name):
                raise ValueError(f"Missing/unsafe indexed frame {expected_frame}")
            ms = record.get("present_ms")
            if type(ms) is not int or ms < ms_start or ms > ms_end or (
                previous_ms is not None and ms < previous_ms
            ):
                raise ValueError(f"Invalid timestamp at indexed frame {expected_frame}")
            source = (folder / name).read_bytes()
            if digest(source) != record.get("png_sha256"):
                raise ValueError(f"Encoded PNG SHA-256 mismatch at frame {expected_frame}")
            try:
                with Image.open(BytesIO(source)) as img:
                    if img.format != "PNG" or img.mode != "P" or img.size != (320, 144):
                        raise ValueError(f"Unexpected native PNG geometry/mode at frame {expected_frame}")
                    indices = img.tobytes()
                    palette = img.getpalette()
            except OSError as exc:
                raise ValueError(f"Cannot decode PNG frame {expected_frame}: {exc}") from exc
            if palette is None or len(palette) != 768:
                raise ValueError(f"Invalid indexed palette at frame {expected_frame}")
            if (digest(indices) != record.get("indexed_sha256") or
                    digest(bytes(palette)) != record.get("palette_sha256")):
                raise ValueError(f"Indexed pixels or palette mismatch at frame {expected_frame}")
            expected_names.add(name)
            expected_frame += 1
            previous_ms = ms
        if previous_ms != ms_end:
            raise ValueError(f"Segment {section_id} end timestamp mismatch")
        previous_tick = last_tick
        segment_meta.append({
            "segment": section_id, "frames": len(entries),
            "first_frame": section["first_frame"], "last_frame": section["last_frame"],
            "omitted_ticks_before": gap,
        })
    actual_names = {item.name for item in folder.glob("frame-*.png")}
    if expected_names != actual_names or manifest.get("frame_count") != expected_frame - 1:
        raise ValueError("PNG inventory or manifest frame count mismatch")
    if not (folder / "play.html").is_file():
        raise ValueError("Missing HTML player")
    return {
        "status": "native_png_integrity_verified",
        "frame_count": expected_frame - 1,
        "indexed_pngs_verified": expected_frame - 1,
        "segments": segment_meta,
        "evidence_boundary": "PNG bytes, indices, palette and metadata only; not a new engine comparison",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_export(args.folder), indent=2))


if __name__ == "__main__":
    main()
