"""Packed DOS VGA depth masks. Set bits occlude actors behind the plane."""
from hashlib import sha256


def _stride(width, height):
    if width <= 0 or width % 8 or height <= 0:
        raise ValueError("Expected a positive strip-aligned mask")
    return width // 8


def pack_plane(pixels, width, height):
    stride = _stride(width, height)
    if len(pixels) != width * height or any(p not in (0, 255) for p in pixels):
        raise ValueError("Invalid binary pixel mask")
    return bytes(sum((128 >> bit) for bit, pixel in enumerate(pixels[i:i + 8]) if pixel)
                 for i in range(0, stride * height * 8, 8))


def crop_plane(packed, width, height, *, x, y, view_width, view_height):
    stride = _stride(width, height)
    view_stride = _stride(view_width, view_height)
    if (len(packed) != stride * height or x % 8 or x < 0 or y < 0
            or x + view_width > width or y + view_height > height):
        raise ValueError("Unsupported mask viewport")
    column = x // 8
    return b"".join(packed[row * stride + column:row * stride + column + view_stride]
                    for row in range(y, y + view_height))


def compose_planes(background, width, height, layers):
    """Redraw from baseline with explicit back-to-front strip writes.

    Each layer supplies x/y, width/height, a mapping of existing plane IDs
    to packed bytes, and one OR/replace flag per strip. Absent planes retain
    existing data. A zero-offset strip is represented as zeros, so its
    replace operation clears and its OR operation retains underlying bits.
    """
    stride = _stride(width, height)
    if any(len(p) != stride * height for p in background.values()):
        raise ValueError("Invalid background mask length")
    result = {key: bytearray(mask) for key, mask in background.items()}
    for x, y, w, h, planes, merge in layers:
        strips = _stride(w, h)
        if x % 8 or len(merge) != strips or not planes.keys() <= result.keys():
            raise ValueError("Unsupported mask layer placement or planes")
        for plane, pixels in planes.items():
            if len(pixels) != strips * h:
                raise ValueError("Invalid object mask length")
            output = result[plane]
            for row in range(max(0, -y), min(h, height - y)):
                for col in range(max(0, -x // 8), min(strips, stride - x // 8)):
                    target = (row + y) * stride + x // 8 + col
                    value = pixels[row * strips + col]
                    output[target] = (output[target] | value) if merge[col] else value
    return {plane: bytes(mask) for plane, mask in result.items()}


def compare_plane(predicted, observed, width, height):
    stride = _stride(width, height)
    if len(predicted) != len(observed) or len(predicted) != stride * height:
        raise ValueError("Invalid packed mask dimensions")
    differing = [(i, a ^ b) for i, (a, b) in enumerate(zip(predicted, observed)) if a != b]
    first = None
    if differing:
        offset, delta = differing[0]
        bit = 8 - delta.bit_length()
        first = dict(offset=offset, bit_msb=bit, x=(offset % stride) * 8 + bit,
                     y=offset // stride, predicted=predicted[offset], observed=observed[offset])
    return dict(bytes_compared=len(predicted), bits_compared=len(predicted) * 8,
                bytes_mismatched=len(differing), bits_mismatched=sum(d.bit_count() for _, d in differing),
                first_mismatch=first, predicted_sha256=sha256(predicted).hexdigest(),
                observed_sha256=sha256(observed).hexdigest())
