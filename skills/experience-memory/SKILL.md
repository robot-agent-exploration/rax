---
name: experience-memory
description: Save successful action tips as soon as they work and retrieve them for later actions under matching observable conditions; distill reusable procedures into learned skills with evidence. Use while controlling the robot, when building automation, and at the start of work or after compaction.
---

# Experience memory

`memory/` belongs to this task and persists across episodes, runs and context
compaction. Keep learned procedures under `memory/skills/`, apart from the provided
skills.

## Retrieve

At the start of work or after compaction, read `memory/INDEX.md` and `memory/TIPS.md`
if present, and open only the learned skills whose conditions match the current scene.
Open linked evidence only when applicability or outcome is uncertain; do not load the
whole history. Current perception and the live tool schemas take precedence over
anything remembered.

## Record tips immediately

- As soon as an action produces a visibly successful, useful result, add or update one
  row in `memory/TIPS.md`. A visible local result is enough; task-level confirmation
  can be added later.
- Record the task phase, the observable preconditions, the tool and arguments or the
  reusable pose relation, the visible effect, and the saved frame paths the tools
  returned. Say what made it work, so later attempts skip the exploration and the
  superseded failures.
- Refine the matching row when the same maneuver improves instead of adding variants.
- Scenes drift between attempts (objects moved back by hand, lighting, layouts): record
  the conditions under which a tip held, not only its numbers.

## Distill

Promote a tip to `memory/skills/<slug>/SKILL.md` plus `evidence.json` when it shows a
reusable motion, contact strategy, recovery or completed procedure. Keep the procedure
short and relative to observed features; keep attempt-specific values and evidence
links in `evidence.json`. Encode poses as the robot's pose-record conventions define
them, when [robot-interface](../robot-interface/SKILL.md) has them.

Update `memory/INDEX.md` with the skill path, tags, confirmation level and the last
episode or date. Mark `task-confirmed` only when the harness's trusted check accepted
an attempt the procedure contributed to, or every `TASK.md` condition was checked in
fresh images; otherwise `observed`. Revise a skill when later evidence contradicts it,
and keep its provenance.

Read [references/format.md](references/format.md) when creating or updating a learned
skill. After writing or changing `memory/`, run the checker and fix every problem it
reports:

```bash
python3 skills/experience-memory/scripts/check_memory.py memory/
```

In a session workspace the same script lives at
`.agents/skills/experience-memory/scripts/check_memory.py`. A worked example is in
[examples/ok](examples/ok). When a procedure has worked unattended and a persistent
library exists, also contribute it there
([continual-learning](../continual-learning/SKILL.md)).

## Code that runs without memory

A controller run for evaluation may not see the editable workspace: put every
procedure it needs into its code before freezing it. When you continue from carried
notes on a new scene, evidence paths may no longer resolve: rely on the stated
conditions and pose recipes, replay relative recipes from the current measured state,
and reacquire every point a recipe anchors to.
