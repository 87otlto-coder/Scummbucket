"""Classic DOS costume scale phases for unclipped world-coordinate composition."""
def reverse_byte(value):
    return int(f'{value:08b}'[::-1], 2)


def threshold(index):
    index %= 256
    if index >= 128:
        return reverse_byte(index - 128)
    if index == 0:
        return 255
    return 253 - reverse_byte(index - 1)


def paint_scaled(costume, pixels, width, x, y, facing, positions, scale):
    """Paint into a mutable indexed plane. Caller supplies draw-phase positions."""
    height = len(pixels) // width
    step = -1 if facing == 270 and not costume.force_right else 1
    dx = dy = 0
    for limb, position in enumerate(positions):
        decoded = costume.limb(limb, position)
        if decoded is None:
            continue
        _, cel = decoded
        rx, ry = dx + cel.rel_x, dy + cel.rel_y
        phase_x = 128 - step * abs(rx)
        phase_y = 128 - abs(ry)
        def kept(index):
            return scale == 255 or threshold(index) < scale
        shift_x = sum(kept(phase_x + step*i) for i in range(abs(rx)))
        shift_y = sum(kept(phase_y + i) for i in range(abs(ry)))
        px = x + step * (shift_x if rx >= 0 else -shift_x)
        top = y + (shift_y if ry >= 0 else -shift_y)
        for col in range(cel.width):
            py = top
            for row in range(cel.height):
                if kept(phase_y + row):
                    slot = cel.slots[col * cel.height + row]
                    if slot and 0 <= px < width and 0 <= py < height:
                        pixels[py * width + px] = costume.palette[slot]
                    py += 1
            if kept(phase_x + step*col):
                px += step
        dx += cel.move_x
        dy -= cel.move_y
