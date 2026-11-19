"""Source-aligned MI2 DOS VGA global entry hook 6 palette writes."""

VGA_ENTRY_PALETTE = {2: (469, 470, 471), 3: (472, 473, 474),
                     1: (475, 476, 477), 6: (478, 479, 480)}


def apply_vga_entry_palette(palette, variables, *, hook, video_mode):
    """Apply the four source writes using explicit pre-hook game variables."""
    if len(palette) != 768 or hook != 6 or video_mode != 19:
        raise ValueError("Expected MI2 DOS VGA global hook 6 and a 256-color palette")
    initialized = bytearray(palette)
    for index, channels in VGA_ENTRY_PALETTE.items():
        rgb = [variables.get(channel) for channel in channels]
        if any(type(value) is not int or not 0 <= value <= 255 for value in rgb):
            raise ValueError(f"Missing or invalid VGA hook operands for palette index {index}")
        initialized[index * 3:index * 3 + 3] = bytes(rgb)
    return bytes(initialized)
