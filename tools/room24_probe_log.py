"""Parse only the explicitly scoped Room 24 and entry-hook probe records."""
import re

from scummbucket.room24_water import choose_nonrepeating


def replay_rng(log, *, initial_state):
    """Replay scoped random calls using one explicit script entry seed.

    The logged previous value is a continuity reference for the script local.
    It never steers a selection or resets the maintained state.
    """
    marker = "SB24 entry room=24 resource=24"
    if log.count(marker) != 1:
        raise ValueError("Expected one Room 24 entry marker")
    rows = re.findall(r"SB24 RNG max=(\d+) result=(\d+) previous=(\d+)",
                      log.split(marker, 1)[1])
    if not rows or initial_state not in (0, 1, 2, 3):
        raise ValueError("Missing Room 24 random calls or invalid entry seed")
    calls = [tuple(map(int, row)) for row in rows]
    if any(maximum != 2 for maximum, _, _ in calls):
        raise ValueError("Unexpected Room 24 RNG maximum")
    choices = choose_nonrepeating((result + 1 for _, result, _ in calls),
                                  (1, 2, 3), previous=initial_state)
    current = initial_state
    pending = []
    batches = []
    for (_, result, observed_previous), (candidate, accepted) in zip(calls, choices):
        if observed_previous != current:
            raise ValueError("Room 24 script-local continuity mismatch")
        pending.append(dict(result=result, candidate=candidate, previous=current,
                            accepted=accepted))
        if accepted:
            current = candidate
            batches.append(pending)
            pending = []
    return batches


def palette_hook(log, room):
    contexts = re.findall(r"SBPAL hook-context room=(\d+) hook=(\d+) mode=(\d+)", log)
    if not contexts:
        return None
    context, = contexts
    actual_room, hook, mode = map(int, context)
    if actual_room != room:
        raise ValueError("Unexpected palette hook probe room")
    rows = re.findall(r"SBPAL var (\d+) (-?\d+)", log)
    variables = {int(key): int(value) for key, value in rows}
    if len(rows) != 12 or set(variables) != set(range(469, 481)):
        raise ValueError("Incomplete or duplicated palette hook variables")
    return hook, mode, variables


def room24_rng(log, states):
    """Align post-transition calls to sampled draws using the source rejection guard."""
    _, marker, after = log.partition("SB24 entry room=24 resource=24")
    if not marker:
        raise ValueError("Room 24 entry marker missing")
    batches = []
    pending = []
    for maximum, result, previous in re.findall(r"SB24 RNG max=(\d+) result=(\d+) previous=(\d+)", after):
        maximum, result, previous = map(int, (maximum, result, previous))
        if maximum != 2 or not 0 <= result <= 2 or not 0 <= previous <= 3:
            raise ValueError("Unexpected Room 24 RNG operands")
        candidate = result + 1
        accepted = candidate != previous
        pending.append(dict(result=result, candidate=candidate, previous=previous, accepted=accepted))
        if accepted:
            batches.append(pending)
            pending = []
    if not batches:
        return None
    if [batch[-1]["candidate"] for batch in batches[:len(states)]] != states:
        raise ValueError("Observed RNG outcomes do not align with sampled states")
    for index, batch in enumerate(batches[:len(states)]):
        previous = states[index - 1] if index else batch[0]["previous"]
        if any(row["previous"] != previous for row in batch):
            raise ValueError("Rejected candidates unexpectedly changed prior state")
    return batches[:len(states)]

