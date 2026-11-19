"""Parse only the explicitly scoped Room 24 and entry-hook probe records."""
import re


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
