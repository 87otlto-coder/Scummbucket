"""One observed v5 Actor::animateCostume call, not a gameplay interpreter.

Ranges and cursor/frame state are supplied by direct before-call observation;
they are not inferred from the actor's latest logical animation selector.
"""
from copy import deepcopy
from .classic_animation import AnimationState, advance


def parse_animation_step(line):
    fields = line.split()
    if len(fields)!=73 or fields[0]!='anim_step' or fields[1] not in ('before','after'):
        raise ValueError('Expected paired anim_step with phase and 71 integer fields')
    try:
        values = [int(v,10) for v in fields[2:]]
    except ValueError as exc:
        raise ValueError('Noninteger animation-step field') from exc
    names = ('id','costume','progress','speed','stopped','animation_counter','sound_counter')
    row = dict(zip(names,values[:7]),phase=fields[1])
    if not 1<=row['id']<=255 or not 1<=row['costume']<=65535:
        raise ValueError('Invalid animation actor/costume identity')
    if any(not 0<=row[n]<=255 for n in ('progress','speed','sound_counter')) or any(
            not 0<=row[n]<=65535 for n in ('stopped','animation_counter')):
        raise ValueError('Animation scalar out of range')
    body = values[7:]
    if any(not 0<=v<=65535 for v in body):
        raise ValueError('Animation limb field out of range')
    row.update(cursors=body[0::4],starts=body[1::4],ends=body[2::4],limb_frames=body[3::4])
    return row


def predict_animation_step(costume,before):
    """Predict actual v5 byte-progress cadence and one bounded COST update."""
    if before['phase']!='before':
        raise ValueError('Prediction requires a before-call observation')
    expected = deepcopy(before)
    expected['phase'] = 'after'
    expected['progress'] = (before['progress']+1)&255
    advanced = expected['progress']>=before['speed']
    changed = False
    if advanced:
        expected['progress'] = 0
        state = AnimationState(cursors=list(before['cursors']),starts=list(before['starts']),
                               ends=list(before['ends']),stopped=before['stopped'],
                               animation_counter=before['animation_counter'],sound_counter=before['sound_counter'])
        changed = advance(costume,state)
        expected.update(cursors=state.cursors,animation_counter=state.animation_counter,
                        sound_counter=state.sound_counter)
    return expected,dict(animation_updated=advanced,cel_changed=changed)


def compare_animation_step(costume,before,after):
    if (before['phase']!='before' or after['phase']!='after' or
            before['id']!=after['id'] or before['costume']!=after['costume']):
        raise ValueError('Animation call identity/phase mismatch')
    expected,operation = predict_animation_step(costume,before)
    differences = {key:dict(predicted=value,observed=after[key])
                   for key,value in expected.items() if value!=after[key]}
    return differences,operation
