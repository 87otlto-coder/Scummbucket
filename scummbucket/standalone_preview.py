"""Build a portable, single-file HTML playback from verified indexed PNG frames.

Source frames stay on disk; their PNG bytes are embedded only into the user-facing
HTML output, never into source control. No ScummVM capture is needed for packaging.
"""
from base64 import b64encode
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
FRAME_NAME = re.compile(r"frame-[0-9]{3}\.png\Z")


def render_standalone_preview(folder, rows, player_template, *, title="Room 7 reconstruction", size=(320, 144)):
    """Return one HTML file containing every PNG as a verified data URI.

    The indexed raster fingerprint is checked against the verifier manifest.
    A missing or malformed PNG fails clearly instead of yielding an inert player.
    """
    folder = Path(folder)
    if not rows:
        raise ValueError("No frames in Room 7 preview manifest")
    if player_template.count("TIMELINE") != 1:
        raise ValueError("Expected exactly one TIMELINE placeholder")
    if player_template.count("Room 23 background") != 1:
        raise ValueError("Unexpected player title placeholder")
    timeline = []
    previous_time = None
    first_time = None
    for i, row in enumerate(rows, 1):
        name = row.get("file")
        if not isinstance(name, str) or not FRAME_NAME.fullmatch(name) or name != f"frame-{i:03}.png":
            raise ValueError(f"Unsafe or out-of-order frame filename at {i}: {name!r}")
        if row.get("frame") != i:
            raise ValueError(f"Unexpected frame number for {name}")
        time = row.get("time_ms")
        if not isinstance(time, int) or (previous_time is not None and time < previous_time):
            raise ValueError(f"Invalid timestamp for {name}")
        if first_time is None:
            first_time = time
        previous_time = time
        path = folder / name
        try:
            png = path.read_bytes()
        except FileNotFoundError as exc:
            raise ValueError(f"Missing PNG frame: {path}") from exc
        if not png.startswith(PNG_SIGNATURE):
            raise ValueError(f"Not a PNG image: {path}")
        try:
            with Image.open(BytesIO(png)) as image:
                if image.format != "PNG" or image.mode != "P" or image.size != size:
                    raise ValueError(f"Unexpected indexed image format/geometry: {path}")
                digest = sha256(image.tobytes()).hexdigest()
        except OSError as exc:
            raise ValueError(f"Could not decode PNG: {path}") from exc
        if digest != row.get("indexed_sha256"):
            raise ValueError(f"Indexed frame SHA-256 mismatch: {path}")
        timeline.append(["data:image/png;base64," + b64encode(png).decode("ascii"), time - first_time])
    return player_template.replace("Room 23 background", title).replace(
        "TIMELINE", json.dumps(timeline, separators=(",", ":"))
    )
