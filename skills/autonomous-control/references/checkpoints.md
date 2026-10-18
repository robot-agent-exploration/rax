# Perception checkpoints

A checkpoint is a point in the controller where the next motion depends on a judgement
from images: before first contact, before closing or opening a gripper, before releasing
or placing, after a base move, after any pause.

## Who perceives what

- **Code** measures geometry: depth, pixel-to-position, kinematics, gripper opening,
  forces.
- **Images** settle semantics: what the objects are, which one is the target, whether
  the gripper is around the object, whether it slipped or tipped, whether the scene
  still matches what the step assumes, why a step failed.

Hand image questions to a subagent where AGENTS.md allows them: a fast model for checks
with a fixed answer form (visible or not, where, how many, is the path clear), a
stronger one for open-ended diagnosis. Their answers are evidence; you decide. When an
answer and the geometry disagree, observe again before acting. A perception subagent
only looks: tell it not to call motion tools.

## The brief a step returns

```python
"checkpoint": {
    "subagent": "<fast | strong>",
    "frames": ["<saved frame path>"],
    "question": "<one question a reader can answer from these frames alone>",
    "answer": "<the answer form, e.g. yes | no, plus a pixel>",
    "pass_if": "<the answer that lets the next step run>",
    "on_fail": "<what the controller or you do next>",
}
```

Write the question so that someone who knows nothing else about the task can answer it:
say what to look at, not what you hope to hear.

## Document every checkpoint

`code/<project>/README.md` keeps a **Perception checkpoints** table, one row per
checkpoint:

| Step | Subagent | Frames | Question | Expected answer | Pass if | On fail |
|---|---|---|---|---|---|---|

Record in the run log where you looked, what you saw and what you decided, so the
checkpoints that matter become visible and the reliable ones can later run unattended.

## Checking

From the repository or a session workspace:

```bash
python3 skills/autonomous-control/scripts/check_controller.py code/<project>/
python3 skills/autonomous-control/scripts/check_controller.py . --json
```

The checker confirms `controller.py` defines `main(ctx)`, returns `{ok, measured, why}`,
never opens `Context()`, and that README documents the run and every checkpoint brief
(or writes `None`). Exit status is 1 when anything breaks the contract. A valid project
is checked in as [examples/ok](../examples/ok). From the repository root run
`python3 skills/run_tests.py`.
