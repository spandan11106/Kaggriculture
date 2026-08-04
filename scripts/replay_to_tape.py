"""Convert a Kaggle replay JSON into a faithful open-loop TAPE agent for one player.

This is the primitive for both:
  - the fresh-snapshot GATE (replay a recorded opponent policy, put our candidate opposite it), and
  - distillation (a medoid trajectory -> a tape our controller can wrap).

Usage:
  python scripts/replay_to_tape.py replays/local_v19.json 0 variants/tape_p0.py
"""
import sys, os, json, zlib, base64

def replay_to_actions(replay_path, player):
    """Extract player's per-step action list from a replay.

    kaggle-environments stores POST-action observations, so the action taken at
    env-step i is recorded at steps[i+1].action (verified: the +1 shift reproduces
    a recorded game exactly). We therefore align tape[i] = steps[i+1].action.
    """
    j = json.load(open(replay_path))
    steps = j["steps"]
    PASS = {"farmer": ["PASS"], "hands": [], "market": []}
    n = len(steps)
    actions = []
    for i in range(n):
        k = i + 1 if i + 1 < n else i
        a = steps[k][player].get("action") if player < len(steps[k]) else None
        actions.append(a if a is not None else PASS)
    return actions

_TEMPLATE = '''import json, zlib, base64
_TAPE = json.loads(zlib.decompress(base64.b85decode({blob!r})))
def agent(obs, config=None):
    # day*24+hour is unambiguous and present for BOTH seats; obs["step"] is
    # stripped from player 1's shared observation.
    step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
    if step >= len(_TAPE):
        step = len(_TAPE) - 1
    return _TAPE[step]
'''

def emit_tape_agent(actions, out_path):
    blob = base64.b85encode(zlib.compress(json.dumps(actions).encode())).decode()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w").write(_TEMPLATE.format(blob=blob))
    return out_path

if __name__ == "__main__":
    replay_path, player, out_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    actions = replay_to_actions(replay_path, player)
    emit_tape_agent(actions, out_path)
    print(f"wrote {out_path} ({len(actions)} steps) from {os.path.basename(replay_path)} player {player}")
