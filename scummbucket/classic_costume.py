"""SCUMM v5 classic DOS 16/32-color costume cels and native-scale composition."""
from dataclasses import dataclass
from struct import Struct


@dataclass(frozen=True)
class Cel:
    width: int
    height: int
    rel_x: int
    rel_y: int
    move_x: int
    move_y: int
    # Local palette slots in column-major order. Slot zero is transparent.
    slots: bytes


class ClassicCostume:
    header = Struct("<HHhhhh")

    def __init__(self, chunk):
        fmt = (chunk[9] & 127) if len(chunk) >= 10 else None
        colors = {0x58: 16, 0x59: 32}.get(fmt)
        if (colors is None or len(chunk) < 44 + colors or
                chunk[:4] != b"COST" or
                int.from_bytes(chunk[4:8], "big") != len(chunk)):
            raise ValueError("expected a complete v5 16/32-color COST")
        self.data = chunk
        self.force_right = bool(chunk[9] & 128)
        self.colors = colors
        self.palette = chunk[10:10 + colors]
        self.table_start = 10 + colors
        self.commands = self.pointer(self.table_start)

    def pointer(self, pos):
        # V5 COST addresses are relative to byte two of the chunk.
        if pos + 2 > len(self.data):
            raise ValueError("truncated COST pointer")
        address = 2 + int.from_bytes(self.data[pos:pos+2], "little")
        if not 10 <= address < len(self.data):
            raise ValueError("invalid COST pointer")
        return address

    def drawn_walk_positions(self, frame, facing, recorded):
        """Undo one tick of a cyclic v5 walk sequence sampled after drawing."""
        directions = {270: 0, 90: 1, 180: 2, 0: 3}
        animation = 4 * frame + directions[facing]
        if frame != 2 or animation > self.data[8] or len(recorded) != 16:
            raise ValueError("unsupported walk animation")
        pos = self.pointer(self.table_start + 34 + 2 * animation)

        def word():
            nonlocal pos
            if pos + 2 > len(self.data):
                raise ValueError("truncated animation record")
            value = int.from_bytes(self.data[pos:pos+2], "little")
            pos += 2
            return value

        mask = word()
        result = list(recorded)
        for limb in range(16):
            if not mask & (0x8000 >> limb):
                if recorded[limb] != 65535:
                    raise ValueError("inherited walk limb is unsupported")
                continue
            start = word()
            if start == 65535 and recorded[limb] == 65535:
                continue
            if start == 65535 or pos >= len(self.data):
                raise ValueError("invalid walk sequence")
            length = self.data[pos]
            pos += 1
            end = start + length
            if length & 128 or self.commands + end >= len(self.data):
                raise ValueError("unsupported walk sequence")
            if self.data[self.commands + start] == 0x79:
                result[limb] = 65535  # Stop preserves the cursor but hides the limb.
                continue
            steps = [i for i in range(start, end + 1)
                     if self.data[self.commands + i] not in (0x78, 0x7c)]
            if recorded[limb] not in steps:
                raise ValueError("recorded limb outside walk sequence")
            result[limb] = steps[steps.index(recorded[limb]) - 1]
        return result

    def limb(self, number, position):
        if not 0 <= number < 16 or not 0 <= position <= 65535:
            raise ValueError("invalid limb state")
        if position == 65535:
            return None
        command = self.commands + (position & 0x7fff)
        if command >= len(self.data):
            raise ValueError("invalid costume sequence position")
        code = self.data[command] & 127
        if code == 0x7b:
            return None
        table = self.pointer(self.table_start + 2 + number * 2)
        offset = self.pointer(table + code * 2)
        if offset + self.header.size > len(self.data):
            raise ValueError("truncated cel header")
        fields = self.header.unpack_from(self.data, offset)
        area = fields[0] * fields[1]
        pos = offset + self.header.size
        if not area or area > 255 * (len(self.data) - pos):
            raise ValueError("invalid cel dimensions")
        slots = bytearray()
        shift = 3 if self.colors == 32 else 4
        mask = (1 << shift) - 1
        while len(slots) < area:
            if pos >= len(self.data):
                raise ValueError("truncated cel")
            encoded = self.data[pos]
            slot, count = encoded >> shift, encoded & mask
            pos += 1
            if count == 0:
                if pos >= len(self.data):
                    raise ValueError("truncated extended run")
                count = self.data[pos]
                pos += 1
            if not count or len(slots) + count > area:
                raise ValueError("invalid cel run length")
            slots.extend(bytes([slot]) * count)
        return offset, Cel(*fields, bytes(slots))


def compose(costume, background, width, x, y, facing, positions):
    """Paint active limbs in order. Return room indices and source placements."""
    if width <= 0 or len(background) % width or len(positions) != 16 or facing not in (0, 90, 180, 270):
        raise ValueError("unsupported geometry or pose")
    height = len(background) // width
    pixels = bytearray(background)
    step = -1 if facing == 270 and not costume.force_right else 1
    dx = dy = 0
    placements = []
    for number, position in enumerate(positions):
        decoded = costume.limb(number, position)
        if decoded is None:
            continue
        offset, cel = decoded
        left = x + step * (dx + cel.rel_x)
        top = y + dy + cel.rel_y
        placements.append(dict(limb=number, position=position, cost_offset=offset,
                               origin=[left, top], x_step=step, size=[cel.width, cel.height]))
        for i, slot in enumerate(cel.slots):
            if slot:
                col, row = divmod(i, cel.height)
                px, py = left + step * col, top + row
                if 0 <= px < width and 0 <= py < height:
                    pixels[py * width + px] = costume.palette[slot]
        dx += cel.move_x
        dy -= cel.move_y
    return bytes(pixels), placements


def apply_depth(indices, background, mask):
    """Apply an MSB-first packed room mask to a flattened indexed pose."""
    if len(indices) != len(background) or len(mask) * 8 != len(indices):
        raise ValueError("incompatible depth mask dimensions")
    return bytes(bg if mask[i // 8] & (128 >> (i % 8)) else pixel
                 for i, (pixel, bg) in enumerate(zip(indices, background)))
