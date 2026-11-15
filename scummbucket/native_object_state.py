"""P4 native indexed SCUMM v5 OBIM state decoder and explicit-position compositor.

The original image palette indices and source transparency remain separate.
No RGB conversion, source archive writes, engine state inference, autoplay,
or assumed object origin. This is a reusable component, NOT proof that a
particular object's live state, drawing order, position or timing was observed.

Uses the bounded, edition-specific strip/mask decoders already covered by
P2 synthetic tests; unsupported codecs and malformed states remain errors.
"""
from __future__ import annotations

from hashlib import sha256
import struct

from .object_images import (
    ImageDecodeError, MAX_IMAGE_STATES, MAX_PIXELS, _decode_zplane, _need,
    _subchunks, decode_strip,
)


def decode_indexed_object_state(
    data: bytes, *, obim_offset: int, state_tag: str,
    transparent_color: int, include_masks: bool = True,
) -> dict:
    """Read a stored IMxx state as original indices + independent alpha mask.

    Opacity is either 0 or 255. A pixel with the room's TRNS index is
    *opaque* when its strip codec does not signal transparency. Therefore
    the original index must never be conflated with alpha.
    """
    _need(type(obim_offset) is int and 0 <= obim_offset <= len(data) - 8,
          "OBIM_OFFSET_INVALID", "OBIM header outside source", offset=obim_offset)
    _need(type(transparent_color) is int and 0 <= transparent_color <= 255,
          "TRNS_INVALID", "Invalid transparent color index")
    _need(isinstance(state_tag, str) and len(state_tag) == 4 and
          state_tag[:2] == "IM" and all(c in "0123456789ABCDEF" for c in state_tag[2:]),
          "STATE_TAG_INVALID", "State must have IMxx hexadecimal tag")
    _need(data[obim_offset:obim_offset + 4] == b"OBIM",
          "OBIM_TAG_INVALID", "Expected OBIM", offset=obim_offset)
    length=struct.unpack_from(">I", data, obim_offset + 4)[0]
    _need(8 <= length <= len(data) - obim_offset,
          "OBIM_LENGTH_INVALID", "OBIM length exceeds source", offset=obim_offset)

    children=_subchunks(data, obim_offset, length)
    headers=[node for node in children if node.tag == "IMHD"]
    _need(len(headers) == 1 and headers[0].length >= 24,
          "IMHD_INVALID", "Expected one full v5 IMHD header", offset=obim_offset)
    object_id, declared=struct.unpack_from("<HH", data, headers[0].offset + 8)
    width,height=struct.unpack_from("<HH", data, headers[0].offset + 20)
    _need(0 < width <= 2048 and width % 8 == 0 and 0 < height <= 1024 and
          width*height <= MAX_PIXELS,
          "IMAGE_DIMENSIONS_UNSUPPORTED", "Unsupported indexed object dimensions",
          offset=headers[0].offset)
    _need(0 < declared <= MAX_IMAGE_STATES,
          "IMAGE_COUNT_UNSUPPORTED", "Unsupported number of object states")
    all_states=[node for node in children if node.tag.startswith("IM") and node.tag!="IMHD"]
    _need(len(all_states) == declared, "IMAGE_COUNT_MISMATCH",
          "IMHD image count differs from stored states", offset=headers[0].offset)
    found=[node for node in all_states if node.tag == state_tag]
    _need(len(found) == 1, "STATE_NOT_FOUND",
          "Requested IMxx state not present exactly once", offset=obim_offset)
    node=found[0]
    parts=_subchunks(data,node.offset,node.length)
    smaps=[part for part in parts if part.tag=="SMAP"]
    _need(len(smaps)==1,"SMAP_INVALID","Expected exactly one state SMAP",offset=node.offset)
    smap=smaps[0]
    strips=width//8
    minimum=8+4*strips
    _need(smap.length >= minimum, "SMAP_TABLE_TRUNCATED",
          "State SMAP strip table too short",offset=smap.offset)
    offsets=[struct.unpack_from("<I",data,smap.offset+8+i*4)[0]
             for i in range(strips)]
    _need(all(minimum<=o<smap.length for o in offsets),
          "SMAP_OFFSET_INVALID", "Object strip offsets outside SMAP",offset=smap.offset)
    _need(all(a<b for a,b in zip(offsets,offsets[1:])),
          "SMAP_OFFSET_ORDER_INVALID", "Object strip offsets overlap",offset=smap.offset)

    pixels=bytearray(width*height)
    opaque=bytearray(b"\xff"*(width*height))
    strip_metadata=[]
    for strip,offset in enumerate(offsets):
        start=smap.offset+offset
        end=smap.offset+(offsets[strip+1] if strip+1<strips else smap.length)
        codec=data[start]
        indices,is_transparent,used=decode_strip(codec,data[start+1:end],height)
        _need(used<=end-start-1,"STRIP_CONSUMPTION_OVERFLOW",
              "Compressed strip consumed beyond own bounds",offset=start)
        _need(not any(data[start+1+used:end]),
              "STRIP_TRAILING_NONZERO",
              "Compressed object strip has nonzero padding",offset=start+1+used)
        for y in range(height):
            dst=y*width+8*strip
            row=indices[y*8:(y+1)*8]
            pixels[dst:dst+8]=row
            if is_transparent:
                opaque[dst:dst+8]=bytes(0 if idx==transparent_color else 255 for idx in row)
        strip_metadata.append(dict(strip=strip,source_offset=start,
                                   codec=codec,used_bytes=used,
                                   has_transparency=is_transparent))
    masks={}
    for part in parts:
        if part.tag.startswith("ZP") and part.tag[2:].isdigit():
            _need(part.tag not in masks, "ZPLANE_DUPLICATE",
                  "Repeated Z plane",offset=part.offset)
            # Decode source mask channels separately. They do not imply a
            # room-plane assignment or that this object was drawn at runtime.
            masks[part.tag]=(_decode_zplane(data,part,width=width,height=height)
                             if include_masks else None)

    native=bytes(pixels)
    alpha=bytes(opaque)
    return dict(
        schema="scummbucket-native-indexed-object-state/1",
        object_id=object_id,state_tag=state_tag,width=width,height=height,
        transparent_index=transparent_color,
        source_offset=node.offset,source_length=node.length,
        pixels=native,opacity=alpha,
        masks={key:value for key,value in masks.items() if value is not None},
        mask_tags=sorted(masks),
        strip_codecs=strip_metadata,
        indexed_sha256=sha256(native).hexdigest(),
        opacity_sha256=sha256(alpha).hexdigest(),
        evidence="original_obim_imxx_decoded",
        observed_live_state=False,
        observed_placement=False,
        observed_timing=False,
    )


def compose_indexed_object(
    background: bytes, background_width: int, background_height: int,
    state: dict, *, x: int, y: int, viewport: tuple[int,int,int,int] | None = None,
    occlusion: bytes | None = None,
) -> bytes:
    """Explicit-position native-indexed overlay, no implicit runtime state.

    (x, y) is supplied by the caller in room pixel coordinates, not
    inferred from OBIM storage or actor/script state. viewport is
    (left,top,width,height). Optional occlusion uses 255 to hide
    object pixels while retaining the prior background pixel; its data
    must cover the whole source room and is not automatically selected.
    """
    w,h=background_width,background_height
    _need(type(w) is int and type(h) is int and 0<w<=2048 and 0<h<=1024
          and w*h<=MAX_PIXELS, "SCENE_DIMENSIONS_INVALID",
          "Unsupported source room geometry")
    _need(len(background)==w*h, "SCENE_PIXEL_LENGTH_INVALID",
          "Source room background index count differs")
    _need(type(x) is int and type(y) is int and
          -100000<=x<=100000 and -100000<=y<=100000,
          "OBJECT_POSITION_INVALID", "Explicit source object origin required")
    if viewport is None:
        viewport=(0,0,w,h)
    _need(isinstance(viewport,tuple) and len(viewport)==4 and
          all(type(n) is int for n in viewport),
          "VIEWPORT_INVALID", "Viewport must be four integers")
    left,top,vw,vh=viewport
    _need(0<=left<w and 0<=top<h and vw>0 and vh>0
          and left+vw<=w and top+vh<=h,
          "VIEWPORT_INVALID", "Viewport outside source room")
    ow,oh=state["width"],state["height"]
    _need(type(ow) is int and type(oh) is int and 0<ow<=2048 and 0<oh<=1024
          and ow*oh<=MAX_PIXELS and
          len(state["pixels"])==ow*oh and len(state["opacity"])==ow*oh,
          "STATE_PIXEL_LENGTH_INVALID", "Native object buffers invalid")
    _need(all(p in (0,255) for p in state["opacity"]),
          "STATE_OPACITY_INVALID", "Opacity is not a binary source mask")
    if occlusion is not None:
        _need(len(occlusion)==w*h and all(p in (0,255) for p in occlusion),
              "OCCLUSION_INVALID", "Occlusion must be a full-room binary mask")
    result=bytearray(vw*vh)
    for row in range(vh):
        src=(top+row)*w+left
        result[row*vw:(row+1)*vw]=background[src:src+vw]
    ix0=max(left,x)
    iy0=max(top,y)
    ix1=min(left+vw,x+ow)
    iy1=min(top+vh,y+oh)
    for yy in range(iy0,iy1):
        original=(yy-y)*ow
        out=(yy-top)*vw
        room=yy*w
        for xx in range(ix0,ix1):
            si=original+xx-x
            if state["opacity"][si] and (
                occlusion is None or not occlusion[room+xx]
            ):
                result[out+xx-left]=state["pixels"][si]
    return bytes(result)
