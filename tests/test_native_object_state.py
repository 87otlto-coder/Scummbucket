"""P4 native object-state tests: synthetic v5 chunks only, no game artwork."""
import struct
import unittest
import zlib
from hashlib import sha256

from scummbucket.native_object_state import (
    decode_indexed_object_state, compose_indexed_object,
)
from scummbucket.object_images import (
    decode_object_state, ImageDecodeError, encode_png,
)
from test_object_images import synth_obim, codec_pixels


class NativeObjectStateTests(unittest.TestCase):
    def setUp(self):
        self.data=synth_obim()
        self.original_hash=sha256(self.data).hexdigest()
        self.palette=bytearray(768)
        self.palette[5*3:5*3+3]=b"\x12\x34\x56"
        self.palette[1*3:1*3+3]=b"\x33\x44\x55"

    def decode(self,tag,**kwargs):
        return decode_indexed_object_state(
            self.data,obim_offset=0,state_tag=tag,transparent_color=5,**kwargs)

    def test_preserves_palette_indices_and_separate_transparency(self):
        first=self.decode("IM01")
        second=self.decode("IM02")
        self.assertEqual(first["object_id"],99)
        self.assertEqual(first["schema"],"scummbucket-native-indexed-object-state/1")
        self.assertEqual((first["width"],first["height"]),(8,8))
        self.assertEqual(first["pixels"],bytes([5]*64))
        self.assertEqual(first["opacity"],bytes(64))
        self.assertEqual(second["pixels"],bytes([1]*64))
        self.assertEqual(second["opacity"],bytes([255]*64))
        self.assertNotEqual(first["indexed_sha256"],second["indexed_sha256"])
        self.assertEqual(first["opacity_sha256"],sha256(bytes(64)).hexdigest())
        self.assertEqual(first["mask_tags"],["ZP01","ZP02","ZP03"])
        self.assertEqual(len(first["masks"]),3)
        self.assertEqual(first["masks"]["ZP02"][:8],bytes([255,0,0,0,0,0,0,255]))
        self.assertFalse(first["observed_live_state"])
        self.assertFalse(first["observed_placement"])
        self.assertFalse(first["observed_timing"])
        self.assertEqual(sha256(self.data).hexdigest(),self.original_hash)

    def test_original_rgba_decoder_agrees_with_native_indices_for_synthetic_states(self):
        for tag in ("IM01","IM02"):
            with self.subTest(state=tag):
                item=self.decode(tag)
                rgba=bytearray()
                for index,alpha in zip(item["pixels"],item["opacity"]):
                    rgba.extend(self.palette[index*3:index*3+3] if alpha else b"\0\0\0")
                    rgba.append(alpha)
                reference_meta,reference_png,_=decode_object_state(
                    self.data,obim_offset=0,state_tag=tag,
                    palette=bytes(self.palette),transparent_color=5)
                self.assertEqual(encode_png(8,8,bytes(rgba),rgba=True),reference_png)
                self.assertEqual(sha256(bytes(rgba)).hexdigest(),
                                 reference_meta["pixel_rgba_sha256"])

    def test_opaque_strip_may_contain_transparency_index_as_opaque_pixel(self):
        # Same TRNS color index 5, but non-transparent codec 68.
        modified=self.data.replace(codec_pixels(68,1),codec_pixels(68,5))
        self.assertNotEqual(modified,self.data)
        state=decode_indexed_object_state(
            modified,obim_offset=0,state_tag="IM02",transparent_color=5)
        self.assertEqual(state["pixels"],bytes([5]*64))
        self.assertEqual(state["opacity"],bytes([255]*64))

    def test_source_rect_and_external_viewport_are_explicit(self):
        state=self.decode("IM02",include_masks=False)
        background=bytes([9]*12*12)
        drawn=compose_indexed_object(background,12,12,state,x=3,y=4)
        for y in range(12):
            for x in range(12):
                self.assertEqual(drawn[y*12+x],1 if 3<=x<11 and 4<=y<12 else 9)
        self.assertEqual(state["masks"],{})
        self.assertEqual(state["mask_tags"],["ZP01","ZP02","ZP03"])
        window=compose_indexed_object(background,12,12,state,x=3,y=4,
                                     viewport=(5,5,4,4))
        self.assertEqual(window,bytes([1]*16))
        offscreen=compose_indexed_object(background,12,12,state,x=90,y=90,
                                        viewport=(5,5,4,4))
        self.assertEqual(offscreen,bytes([9]*16))

    def test_clipping_transparency_and_explicit_occlusion(self):
        state=self.decode("IM02")
        background=bytes([7]*8*8)
        occlusion=bytearray(8*8)
        occlusion[2*8]=255
        result=compose_indexed_object(background,8,8,state,x=-3,y=2,
                                      occlusion=bytes(occlusion))
        self.assertEqual(result[2*8],7)
        self.assertEqual(result[2*8+1],1)
        self.assertEqual(result[2*8+4],1)
        self.assertEqual(result[2*8+5],7)
        self.assertEqual(result[:2*8],bytes([7]*16))
        transparent=self.decode("IM01")
        self.assertEqual(compose_indexed_object(
            background,8,8,transparent,x=0,y=0),background)

    def test_bad_source_opcode_and_state_count_fail_without_fallback(self):
        for modified,tag,code in (
            (synth_obim(bad_code=251),"IM01","STRIP_CODEC_UNSUPPORTED"),
            (self.data,"IM03","STATE_NOT_FOUND"),
            (b"XXXX"+self.data[4:],"IM01","OBIM_TAG_INVALID"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(ImageDecodeError) as exc:
                    decode_indexed_object_state(
                        modified,obim_offset=0,state_tag=tag,transparent_color=5)
                self.assertEqual(exc.exception.code,code)

    def test_overlay_refuses_invalid_lengths_alpha_mask_and_geometry(self):
        state=self.decode("IM02")
        bg=bytes([7]*64)
        cases=[
            (dict(state,pixels=b""),{}, "STATE_PIXEL_LENGTH_INVALID"),
            (dict(state,opacity=bytes([10]*64)),{}, "STATE_OPACITY_INVALID"),
            (state,dict(occlusion=b""),"OCCLUSION_INVALID"),
            (state,dict(viewport=(0,0,9,8)),"VIEWPORT_INVALID"),
            (state,dict(x=True),"OBJECT_POSITION_INVALID"),
        ]
        for candidate,options,code in cases:
            with self.subTest(code=code):
                kwargs=dict(x=0,y=0)
                kwargs.update(options)
                with self.assertRaises(ImageDecodeError) as exc:
                    compose_indexed_object(bg,8,8,candidate,**kwargs)
                self.assertEqual(exc.exception.code,code)


if __name__ == "__main__":
    unittest.main()
