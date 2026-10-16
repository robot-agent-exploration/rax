---
name: autonomous-control
description: Turn what worked by hand into a step-wise Python controller, controller.py:main(ctx), that re-perceives the scene and completes the task from a fresh start; develop, debug and test it end to end. Use after a confirmed manual success, for closed-loop scripts, and when switching between your code and direct control.
---

# Autonomous control

The deliverable is a controller that completes the task from a fresh scene: the code
does the motions and measurements, re-localizes everything it acts on, checks each
step, and stops with a clear report when the scene is not what it was built for.
AGENTS.md says how it is judged: run alone on unseen scenes, or run by you with your
perception checking the decisive points.

## Start from your manual success

Read the saved strategy and decisive frames in `memory/`. Create `code/<project>/` and
turn one useful maneuver into a function that takes `ctx` and explicit inputs. Test it
on the current scene, inspect its final images and logs, fix it, and repeat before
composing the whole `main(ctx)`. Reproduce the decisions that made the manual run
work, not its recorded actions.

## Model the invariant motion; perceive what changes

A new layout should need new perception and parameters, not new motion code.

- **Invariant motion in the object's frame.** Write approach standoffs, directions,
  grasp offsets, lift heights and the contact strategy relative to the object or
  target, never as coordinates from one run.
- **A perception layer with a fixed output.** One function turns the current scene
  into a small description the motions consume (target pose and size, support height,
  obstacles). Geometry comes from depth, camera geometry and kinematics; semantic
  judgements (which object, is it held, did it tip) come from images, through you, a
  [VLM](../vlm-perception/SKILL.md) or a perception subagent.
- **Three layers.** Perception, motion primitives (each with its own checks) and a
  short task script that chains them, in separate modules.
- **Parameters as data.** Object descriptions, tolerances and per-scene settings live
  in one config with the range each was tested on. A scene outside a tested range is
  a reason to stop and look, not to extrapolate.
- **Choose at run time.** Pick the arm, approach side and posture from the perceived
  scene: reason out a few candidates, check them with the robot's dry-run tools
  (`<preview>`), and take the first that passes. Do not grid-search.
- Prefer simple motion functions and rules; use the VLM where simple rules break on
  new views.

## Steps you can read, resume and supervise

- Split the pipeline into steps, each with an observable precondition and completion
  check.
- Each step `fn(ctx, ...)` checks its preconditions from fresh observations, acts,
  verifies the result and returns `{"ok": bool, "measured": {...}, "why": str}` plus
  the frames it used. Outside what it was tested on, it returns instead of
  improvising, leaving the robot safe: nothing held dropped mid-air, arm clear,
  nothing moving.
- Make the pipeline resumable at any step, and give every motion that can fail a
  fallback.
- Keep tunable values as named constants at the top of a module, with their tested
  ranges.
- `controller.py:main(ctx)` chains the steps, stops at the first failure and returns a
report. `code/<project>/README.md` says how to run the whole controller and each
step, with their preconditions.

After writing or changing the project, run the checker and fix every problem it
reports:

```bash
python3 skills/autonomous-control/scripts/check_controller.py code/<project>/
```

In a session workspace the same script lives at
`.agents/skills/autonomous-control/scripts/check_controller.py`. Pass the workspace
root to scan every `code/<project>/`. A worked example is in [examples/ok](examples/ok).

When AGENTS.md keeps you in the loop, each step that ends where a mistake would drop,
crush or knock something returns a checkpoint for you or a subagent to settle from the
frames alone; see [references/checkpoints.md](references/checkpoints.md). Chain steps
without looking only where their own checks have caught the failures you saw.

## Ordinary Python

Write the controller against a supplied context. The entrypoint is the same in
development and in every test or evaluation run:

```python
# code/<project>/controller.py
import json

def main(ctx):
    reply = ctx.call("<observe>")            # {"content": [text and image blocks]}
    state = json.loads(reply["content"][0]["text"])
    # observation -> decision -> action, e.g. ctx.call("<move_pose>", **target)
    return {"ok": True, "measured": {}, "why": ""}
```

Only a development wrapper, kept outside `code/<project>/` and run from the workspace
root, opens the context:

```python
# experiments/run_controller.py
import sys
from api.runtime import Context

sys.path.insert(0, "code/<project>")
from controller import main

with Context() as ctx:
    print(main(ctx))
```

- `main(ctx)` and its helpers use the supplied context unchanged and pass it down;
  they never open a new `Context()`.
- `ctx.call(tool, **arguments)` uses the live tool schemas (`MCP_SESSION.md`) and
  returns MCP content blocks; JSON metadata is in the text block, images stay image
  blocks. Inspect the schemas instead of inventing arguments.
- A tool error raises `RuntimeError` carrying the full error. Handle refusals in code;
  never retry the same motion blindly.
- Robot calls run one at a time, but a script does not own the robot: your direct
  calls can interleave with it. Run one controller at a time and stop it before you
  act directly.
- Interrupting Python does not cancel a dispatched motion. After an interruption or an
  ambiguous error, check `<status>` and a fresh observation before continuing.
- Returning does not reset the scene: it keeps the script's actions, so you can
  inspect and continue by hand.
- Save replies, decisions and prints under `output/`; the harness keeps the robot's
  own frames and traces.

## Test end to end

1. Start each test from a fresh scene as AGENTS.md provides it: a new episode, or an
   operator reset after you bring the robot to its neutral state
   ([robot-interface](../robot-interface/SKILL.md)).
2. Commit the controller version and run it once, unattended: no direct robot calls
   while it runs. A run you finished by hand is debugging, not a success.
3. Record every run in memory: code version, scene, outcome, duration, failing step
   and cause, and where you looked if you supervised it.
4. Vary what the invariants claim not to depend on (position, orientation, distance,
   side, distractors, lighting). A variation that breaks the code shows which quantity
   was not perceived. Do not claim untested generalization.

Where the harness freezes the controller for evaluation, the frozen run sees only its
own project directory, its own frames and a fresh output directory: keep every module
and data file under `code/<project>/`, open bundled files relative to `__file__`,
write under `output/`, and leave margin under the episode's wall limit.
