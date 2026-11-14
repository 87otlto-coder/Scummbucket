"""Shared native indexed-animation integrity and HTML timeline primitives.

The module is room-agnostic. It neither decodes game files nor validates an
engine trace by itself; callers must establish their own evidence boundary.
No private frames or game resources are embedded in source control.
"""
from base64 import b64encode
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def inspect_indexed_png(path, *, size, index_sha, palette_sha, png_sha):
    """Verify actual PNG bytes, decoded indices and full 768-byte palette."""
    path = Path(path)
    raw = path.read_bytes()
    if not raw.startswith(PNG_SIGNATURE) or sha256(raw).hexdigest() != png_sha:
        raise ValueError(f"PNG file digest/format mismatch: {path.name}")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or image.mode != "P" or image.size != tuple(size):
                raise ValueError(f"Unexpected native indexed image geometry/mode: {path.name}")
            pixels = image.tobytes()
            palette = image.getpalette()
    except OSError as exc:
        raise ValueError(f"Cannot decode native indexed image: {path.name}") from exc
    if palette is None or len(palette) != 768:
        raise ValueError(f"Invalid 768-byte indexed palette: {path.name}")
    if sha256(pixels).hexdigest() != index_sha:
        raise ValueError(f"Indexed pixel digest mismatch: {path.name}")
    if sha256(bytes(palette)).hexdigest() != palette_sha:
        raise ValueError(f"Indexed palette digest mismatch: {path.name}")
    return raw


def embed_segment_timeline(template, segments, *, marker):
    """Serialize already validated JSON-compatible segments into an HTML template.

    This is the common serialization boundary. Room-specific templates own
    the semantic labels and playback controls; no JSON is built from raw
    archive/script data inside browser code.
    """
    if not isinstance(segments, list) or not segments:
        raise ValueError("Need nonempty source-verified animation segments")
    if template.count(marker) != 1:
        raise ValueError("HTML player must contain exactly one timeline marker")
    return template.replace(marker, json.dumps(segments, separators=(",", ":")))


def frame_data_uri(png):
    """Embed a verified PNG only, for single-file offline playback."""
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("Only PNG images can be embedded")
    return "data:image/png;base64," + b64encode(png).decode("ascii")
