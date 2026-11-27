"""Optional BigR M1 sidecar; no SCUMM decoding or scaling engine here."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

CONTRACT = "bigr.export.cli.v1"
SCHEMA = "bigr.asset.v1"
PIXELS = "data/raster-pixels.bin"


class BackendError(RuntimeError):
    """BigR failed or cannot safely satisfy the request."""
    def __init__(self, code, message, diagnostic=None):
        super().__init__(message)
        self.code = code
        self.diagnostic = diagnostic


def digest(data):
    return sha256(data).hexdigest()


def canonical(value):
    # This adapter emits only ASCII keys/strings and integer values, matching
    # BigR's canonical JSON for this deliberately restricted package.
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


@dataclass(frozen=True)
class Raster:
    width: int
    height: int
    rgba: bytes
    source_png: bytes
    provenance: dict


def load_raster(png, room7_manifest=None):
    """Accept explicit RGBA PNG or the previously verified Room 7 P-mode export.

    A Room 7 manifest is evidence supplied by the caller, not a new runtime
    comparison. Preserve original PNG and all index/palette evidence at source.
    """
    from PIL import Image
    png = Path(png)
    raw = png.read_bytes()
    evidence = {"extractor": "ScummBucket", "sourcePngSha256": digest(raw)}
    with Image.open(BytesIO(raw)) as im:
        if im.format != "PNG" or getattr(im, "n_frames", 1) != 1:
            raise ValueError("Expected a single decoded PNG raster")
        if im.width * im.height > 4_000_000:
            raise ValueError("Source exceeds adapter's M1 raster safety limit")
        im.load()
        if room7_manifest is None:
            if im.mode != "RGBA":
                raise ValueError("Explicit RGBA PNG required; indexed palette confidence is not inferred")
            evidence["confidence"] = "caller-supplied-decoded-raster"
        else:
            mr = Path(room7_manifest).read_bytes()
            m = json.loads(mr)
            if (m.get("schema") != "room7-navigation-native-export/1"
                    or m.get("room_id") != 7
                    or m.get("edition") != "Monkey Island 2, original DOS VGA"
                    or m.get("geometry") != [320, 144]
                    or m.get("all_indexed_comparisons_exact") is not True
                    or m.get("palette_source") !=
                    "engine-observed post-presentation palette; not independently forecast here"
                    or im.mode != "P" or im.size != (320, 144)
                    or "transparency" in im.info):
                raise ValueError("Not an opaque, verified Room 7 viewport export")
            rows = [f for s in m["segments"] for f in s["frames"]
                    if f.get("file") == png.name]
            if len(rows) != 1:
                raise ValueError("Room 7 frame missing or ambiguous")
            row = rows[0]
            palette = bytes(im.getpalette() or [])
            indices = im.tobytes()
            if (len(palette) != 768 or row.get("png_sha256") != digest(raw)
                    or row.get("indexed_sha256") != digest(indices)
                    or row.get("palette_sha256") != digest(palette)):
                raise ValueError("Room 7 PNG/index/palette hashes do not match evidence")
            evidence.update(confidence="manifest-attested-index-and-engine-palette",
                            room=7, frame=row["frame"],
                            sourceManifestSha256=digest(mr),
                            indexedSha256=digest(indices), paletteSha256=digest(palette))
        rgba = im.convert("RGBA")
        return Raster(im.width, im.height, rgba.tobytes(), raw, evidence)


def make_package(raster, asset_id, directory):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", asset_id)
            or ".." in asset_id):
        raise ValueError("Invalid BigR asset ID")
    if (type(raster.width) is not int or type(raster.height) is not int
            or raster.width < 1 or raster.height < 1
            or len(raster.rgba) != raster.width * raster.height * 4):
        raise ValueError("Invalid tightly packed RGBA8 raster")
    m = {"schema": SCHEMA, "assetId": asset_id, "kind": "raster",
         "raster": {"width": raster.width, "height": raster.height,
                    "format": "rgba8", "pixels": PIXELS},
         "payloads": {PIXELS: {"byteLength": len(raster.rgba),
                              "sha256": digest(raster.rgba)}},
         "provenance": raster.provenance}
    data = canonical(m)
    directory = Path(directory)
    directory.mkdir()
    (directory / "data").mkdir()
    (directory / PIXELS).write_bytes(raster.rgba)
    (directory / "manifest.json").write_bytes(data)
    return digest(data)


class BigR:
    def __init__(self, cli=None, node="node", timeout=120):
        cli = cli or os.environ.get("BIGR_EXPORT_CLI")
        if not cli or not Path(cli).is_file() or not shutil.which(str(node)):
            raise BackendError("UNAVAILABLE", "Configure a built BigR CLI and Node executable")
        self.command = [str(Path(shutil.which(str(node))).resolve()), str(Path(cli).resolve())]
        self.timeout = timeout

    def run(self, *args):
        try:
            p = subprocess.run(self.command + list(map(str, args)), shell=False,
                               capture_output=True, encoding="utf-8", errors="replace",
                               timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BackendError("PROCESS_FAILURE", str(exc)) from exc
        if p.returncode:
            try:
                d = json.loads(p.stderr)
                err = d["error"]
                if (d["ok"] is not False or d["contract"] != CONTRACT
                        or not isinstance(err["code"], str)):
                    raise ValueError("invalid error envelope")
            except (ValueError, KeyError, TypeError):
                raise BackendError("PROCESS_FAILURE", f"Exit {p.returncode}: {p.stderr[:2000]}")
            raise BackendError(err["code"], str(err.get("message", "")), d)
        try:
            d = json.loads(p.stdout)
            if not isinstance(d, dict) or d.get("ok") is not True or d.get("contract") != CONTRACT:
                raise ValueError("invalid success envelope")
        except (ValueError, TypeError) as exc:
            raise BackendError("INVALID_RESPONSE", str(exc)) from exc
        return d

    def capabilities(self):
        d = self.run("capabilities")
        try:
            r = d["render"]
            checks = [(d["commands"], ("capabilities", "validate", "render")),
                      (r["supportedKinds"], ("raster",)), (r["inputPixelFormats"], ("rgba8",)),
                      (r["outputFormats"], ("png",)), (r["scalingMethods"], ("nearest",))]
            if (d["packageSchema"] != SCHEMA or not isinstance(d["appVersion"], str)
                    or any(not isinstance(a, list) or any(v not in a for v in b)
                           for a, b in checks)
                    or r["scale"] != "uniform positive integer (default 1)"
                    or type(r["maxOutputPixels"]) is not int or r["maxOutputPixels"] < 1):
                raise ValueError("incompatible schema or required rendering capability")
        except (KeyError, TypeError, ValueError) as exc:
            raise BackendError("INCOMPATIBLE", str(exc)) from exc
        return d


def verify_output(folder, report, raster, scale, asset_id, source_hash):
    from PIL import Image
    try:
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("Missing output directory")
        if set(p.name for p in folder.iterdir()) != {"image.png", "result.json"}:
            raise ValueError("Unexpected output files")
        if any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
            raise ValueError("Output files must be regular files")
        disk = json.loads((folder / "result.json").read_bytes())
        if disk != report or disk.get("status") != "complete":
            raise ValueError("Result manifest/stdout disagreement")
        expected_source = {"assetId": asset_id, "packageSchema": SCHEMA,
                           "manifestSha256": source_hash}
        expected_render = {"method": "nearest", "scaleX": scale, "scaleY": scale}
        size = (raster.width * scale, raster.height * scale)
        png = (folder / "image.png").read_bytes()
        expected_output = {"path": "image.png", "format": "png", "pixelFormat": "rgba8",
                           "width": size[0], "height": size[1], "sha256": digest(png)}
        if (disk.get("source") != expected_source or disk.get("rendering") != expected_render
                or disk.get("output") != expected_output
                or not isinstance(disk.get("warnings"), list)
                or not isinstance(disk.get("encoder"), dict)):
            raise ValueError("Result provenance, dimensions, rendering or digest mismatch")
        with Image.open(BytesIO(png)) as im:
            if im.format != "PNG" or im.mode != "RGBA" or im.size != size:
                raise ValueError("Unexpected PNG format, mode or dimensions")
            actual = im.tobytes()
        # Pillow is an independent reference; never used for the BigR output itself.
        reference = Image.frombytes("RGBA", (raster.width, raster.height), raster.rgba)
        expected = reference.resize(size, Image.Resampling.NEAREST).tobytes()
        if actual != expected:
            raise ValueError("Decoded RGBA pixels differ from independent reference")
        return {"rgbaSha256": digest(actual), "pixelMismatches": 0,
                "comparedPixels": size[0] * size[1]}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise BackendError("OUTPUT_VERIFICATION_FAILED", str(exc)) from exc


def export(png, output, *, asset_id, scale=1, cli=None, node="node",
           room7_manifest=None, fallback_native=False):
    """Publish only a verified BigR result, or an explicitly marked native fallback."""
    if type(scale) is not int or scale < 1:
        raise ValueError("Scale must be a positive integer")
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError(str(output))
    raster = load_raster(png, room7_manifest)
    if not output.parent.is_dir():
        raise ValueError("Output parent must exist")
    with tempfile.TemporaryDirectory(prefix=".scummbucket-bigr-", dir=output.parent) as tmp:
        root = Path(tmp)
        package, rendered = root / "package", root / "rendered"
        source_hash = make_package(raster, asset_id, package)
        try:
            backend = BigR(cli, node)
            caps = backend.capabilities()
            if raster.width * raster.height * scale * scale > min(
                    caps["render"]["maxOutputPixels"], 4_000_000):
                raise BackendError("UNSUPPORTED_FEATURE", "Requested output exceeds pixel limit")
            checked = backend.run("validate", "--input", package)
            if (checked.get("valid") is not True or checked.get("pngRenderable") is not True
                    or checked.get("assetId") != asset_id or checked.get("kind") != "raster"
                    or checked.get("packageSchema") != SCHEMA
                    or checked.get("sourceManifestSha256") != source_hash
                    or checked.get("payloadCount") != 1):
                raise BackendError("INVALID_VALIDATION", "BigR did not validate the exact package")
            report = backend.run("render", "--input", package, "--output", rendered,
                                 "--scale", scale)
            verification = verify_output(rendered, report, raster, scale, asset_id, source_hash)
            if ((package / "manifest.json").read_bytes() != canonical(json.loads(
                    (package / "manifest.json").read_bytes()))
                    or digest((package / "manifest.json").read_bytes()) != source_hash
                    or (package / PIXELS).read_bytes() != raster.rgba):
                raise BackendError("INPUT_MUTATED", "BigR changed the staged package")
            summary = {"status": "complete", "backend": "BigR", "requestedScale": scale,
                       "actualScale": scale, "capabilities": caps, "validation": checked,
                       "verification": verification, "provenance": raster.provenance}
            publish = {"image.png": (rendered / "image.png").read_bytes(),
                       "result.json": (rendered / "result.json").read_bytes()}
        except BackendError as exc:
            if not fallback_native:
                raise
            summary = {"status": "fallback-native", "backend": "ScummBucket",
                       "requestedScale": scale, "actualScale": 1,
                       "error": {"code": exc.code, "message": str(exc),
                                 "diagnostic": exc.diagnostic},
                       "provenance": raster.provenance,
                       "outputSha256": digest(raster.source_png)}
            # Exact existing native export, no new scaling or invented colors.
            publish = {"image.png": raster.source_png}
        publish["adapter.json"] = canonical(summary)
        # Exclusive directory creation refuses existing files/directories even if
        # another export won the race. Only remove our own partial publication.
        output.mkdir()
        try:
            for name, contents in publish.items():
                with (output / name).open("xb") as handle:
                    handle.write(contents)
            if summary["status"] == "complete":
                shutil.copytree(package, output / "package")
        except BaseException:
            shutil.rmtree(output)
            raise
        return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("png", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--scale", type=int, default=1)
    p.add_argument("--bigr-cli", type=Path)
    p.add_argument("--node", default="node")
    p.add_argument("--room7-manifest", type=Path)
    p.add_argument("--fallback-native", action="store_true")
    a = p.parse_args(argv)
    try:
        result = export(a.png, a.output, asset_id=a.asset_id, scale=a.scale,
                        cli=a.bigr_cli, node=a.node, room7_manifest=a.room7_manifest,
                        fallback_native=a.fallback_native)
    except (BackendError, OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        import sys
        print(json.dumps({"status": "failed", "error": {"code": getattr(exc, "code", "SOURCE_OR_IO"),
                          "message": str(exc), "diagnostic": getattr(exc, "diagnostic", None)}}),
              file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
