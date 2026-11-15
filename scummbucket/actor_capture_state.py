"""Parse pre-redraw state observations separately from actual draw operations.

No cached pose is inserted, no timing is predicted, and no state row is called
a framebuffer snapshot. Scale/renderer preparation can occur after this phase.
"""
STATE_FIELDS = ['id', 'world_x', 'world_y', 'elevation', 'screen_x', 'draw_y',
                'room', 'visible', 'need_redraw', 'need_bg_reset', 'scale_x', 'scale_y',
                'facing', 'costume', 'logical_frame', 'walkbox', 'force_clip', 'never_clip',
                'layer', 'anim_progress', 'anim_speed', 'stopped', 'plane', 'draw_to_back',
                'shadow_mode', 'top', 'bottom']


def parse_actor_state_record(line):
    fields = line.split()
    if len(fields) != 76 or fields[0] != 'state_actor':
        raise ValueError('Expected state_actor plus 75 integer fields')
    try:
        values = [int(v, 10) for v in fields[1:]]
    except ValueError as exc:
        raise ValueError('Noninteger actor state field') from exc
    row = dict(zip(STATE_FIELDS, values[:27]))
    row['cursors'] = values[27:43]
    row['palette_override'] = values[43:75]
    if not 1 <= row['id'] <= 255 or not 0 <= row['room'] <= 255:
        raise ValueError('Actor/room identity out of range')
    if row['facing'] not in (0, 90, 180, 270):
        raise ValueError('Unsupported actor facing')
    for name in ('visible', 'need_redraw', 'need_bg_reset', 'never_clip', 'draw_to_back'):
        if row[name] not in (0, 1):
            raise ValueError(f'Invalid actor boolean: {name}')
    for name in ('scale_x', 'scale_y', 'walkbox', 'force_clip', 'anim_progress',
                 'anim_speed', 'plane', 'shadow_mode'):
        if not 0 <= row[name] <= 255:
            raise ValueError(f'Actor byte field out of range: {name}')
    if any(not 0 <= row[name] <= 65535 for name in ('costume', 'logical_frame', 'stopped')):
        raise ValueError('Costume/frame/stopped field out of range')
    if any(not -(2**31) <= row[name] < 2**31
           for name in ('world_x', 'world_y', 'elevation', 'screen_x', 'draw_y', 'layer', 'top', 'bottom')):
        raise ValueError('Actor coordinate/layer/bounds outside signed 32-bit range')
    if any(not 0 <= v <= 65535 for v in row['cursors']) or any(
            not 0 <= v <= 255 for v in row['palette_override']):
        raise ValueError('Actor cursor/palette field out of range')
    return row


def compare_state_to_draw(state, draw):
    """Report phase differences; do not silently prefer a state over a draw."""
    if state['id'] != draw['id']:
        raise ValueError('Actor state/draw identity mismatch')
    expected = dict(id=state['id'], screen_x=state['screen_x'], draw_y=state['draw_y'],
                    plane=state['plane'], scales=[state['scale_x'], state['scale_y']],
                    facing=state['facing'], costume=state['costume'],
                    logical_frame=state['logical_frame'], stopped=state['stopped'],
                    cursors=state['cursors'], palette_override=state['palette_override'])
    return {name: dict(before_prepare=value, actual_draw=draw[name])
            for name, value in expected.items() if value != draw[name]}
