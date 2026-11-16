"""Bounded SCUMM v5 COST state experiment, referenced to ScummVM v2026.4.0.

This models animation updates, not engine ticks or wall-clock timing. Source
lineage remains subject to the existing P4 review. No game data is embedded.
"""
from dataclasses import dataclass, field

@dataclass
class AnimationState:
    cursors: list[int] = field(default_factory=lambda: [65535]*16)
    starts: list[int] = field(default_factory=lambda: [0]*16)
    ends: list[int] = field(default_factory=lambda: [0]*16)
    stopped: int = 0
    animation_counter: int = 0
    sound_counter: int = 0
    # v5 CostumeData.frame is the selected direction-specific animation index.
    # It is changed on new cel/clear, but not by stop/resume controls.
    limb_frames: list[int] = field(default_factory=lambda: [65535]*16)

    def visible_positions(self):
        return [65535 if self.stopped & (1 << i) else p for i,p in enumerate(self.cursors)]


def initialize(costume, state, frame, facing, usemask=65535):
    """Apply an explicitly selected v5 animation record; no scripts/timing.

    Parse the record before applying any limb update. Malformed later limbs
    must not leave an apparently valid, partially changed animation state.
    """
    directions = {270: 0, 90: 1, 180: 2, 0: 3}
    if (facing not in directions or type(frame) is not int or frame < 0 or
            type(usemask) is not int or not 0 <= usemask <= 65535):
        raise ValueError('Invalid animation selector')
    if any(len(field) != 16 for field in
           (state.cursors, state.starts, state.ends, state.limb_frames)):
        raise ValueError('Invalid animation limb state width')
    animation = frame * 4 + directions[facing]
    if animation > costume.data[8]:
        return False
    table = costume.table_start + 34 + 2 * animation
    if table + 2 > len(costume.data):
        raise ValueError('Truncated animation table')
    if costume.data[table:table + 2] == b'\0\0':
        return False
    offset = costume.pointer(table)

    def word():
        nonlocal offset
        if offset + 2 > len(costume.data):
            raise ValueError('Truncated animation record')
        value = int.from_bytes(costume.data[offset:offset + 2], 'little')
        offset += 2
        return value

    mask = word()
    pending = []
    for limb in range(16):
        bit = 32768 >> limb
        if not mask & bit:
            continue
        start = word()
        extra = None
        if start != 65535:
            if offset >= len(costume.data):
                raise ValueError('Missing animation extent')
            extra = costume.data[offset]
            offset += 1
        # ScummVM consumes the record even if the usemask excludes this limb.
        # No command/range evaluation should be inferred for excluded limbs.
        if not usemask & bit:
            continue
        if start == 65535:
            pending.append((limb, 'clear', None, None))
            continue
        if costume.commands + start >= len(costume.data):
            raise ValueError('Animation command outside COST')
        command = costume.data[costume.commands + start]
        if command == 0x79:
            pending.append((limb, 'stop', None, None))
        elif command == 0x7a:
            pending.append((limb, 'resume', None, None))
        else:
            end = start + (extra & 127)
            if costume.commands + end >= len(costume.data):
                raise ValueError('Animation range outside COST')
            pending.append((limb, 'select', start, (end, bool(extra & 128))))

    for limb, operation, start, extent in pending:
        if operation == 'clear':
            state.cursors[limb] = 65535
            state.starts[limb] = 0
            state.limb_frames[limb] = animation
        elif operation == 'stop':
            state.stopped |= 1 << limb
        elif operation == 'resume':
            state.stopped &= ~(1 << limb)
        else:
            end, one_shot = extent
            state.starts[limb] = start
            state.ends[limb] = end
            state.cursors[limb] = start | (32768 if one_shot else 0)
            state.limb_frames[limb] = animation
    return True


def advance(costume, state):
    """Advance once; return changed-cel flag and preserve control side effects."""
    changed=False
    for limb,cursor in enumerate(state.cursors):
        if cursor==65535: continue
        high=cursor&32768; current=cursor&32767
        start,end=state.starts[limb],state.ends[limb]
        if not 0<=start<=current<=end or costume.commands+end>=len(costume.data):
            raise ValueError('Invalid animation execution range')
        old=costume.data[costume.commands+current]&127
        seen=set()
        while True:
            current=min(current+1,end) if high else (start if current>=end else current+1)
            if current in seen: raise ValueError('Control-only animation cycle')
            seen.add(current)
            code=costume.data[costume.commands+current]
            if code==0x7c: state.animation_counter=(state.animation_counter+1)&65535
            elif code==0x78: state.sound_counter=(state.sound_counter+1)&255
            if code in (0x78,0x7c) and start!=end: continue
            state.cursors[limb]=current|high
            changed |= (code&127)!=old
            break
    return changed
