# Learned memory format

Store learned skills only below `memory/skills/`, each under a lowercase hyphenated slug.

## `TIPS.md`

One row per reusable local result; update a matching row instead of adding variants of
the same lesson:

```markdown
| Task phase | Preconditions | What worked | Visible effect | Evidence |
|---|---|---|---|---|
| <phase> | <observable conditions> | <tool and arguments, or pose relation> | <visible change> | <saved frame path> |
```

## `INDEX.md`

```markdown
| Skill | Tags | Confirmation | Last confirmed |
|---|---|---|---|
| `skills/<slug>/SKILL.md` | <tags> | observed | <episode id or date> |
```

`Confirmation` is `observed` for a clear local visual effect, or `task-confirmed` when
the procedure contributed to an attempt the harness's trusted check accepted, or in
which every `TASK.md` condition was checked in fresh images.

## Generated `SKILL.md`

```markdown
---
name: learned-<slug>
description: <maneuver and when this experience applies>
---

# <name>

- Applies when: <observable conditions>
- Avoid when: <observable mismatch>
- Executed action: <tool and exact arguments>
- Pose recipe: <anchor, frame, offset>
- Actions: <compact ordered procedure>
- Expected effect: <visible result>
- Recovery: <evidence-backed alternative>
```

Do not copy tool documentation or robot limits into a learned skill, and do not encode
hidden state, inferred task success or an unobserved object pose.

## `evidence.json`

```json
{
  "schema_version": 1,
  "skill": "learned-<slug>",
  "examples": [
    {
      "task": "<task>",
      "episode_or_date": "<episode id or ISO date>",
      "confirmation": "observed | task-confirmed",
      "frames": ["<saved frame or manifest path>"],
      "executed_action": {"tool": "<tool>", "arguments": {}},
      "pose_recipe": "<anchor, frame, offset>",
      "point_reacquisition": "<visible feature, offset, localization method, preferred views>",
      "observed_effect": "<visible change>"
    }
  ]
}
```

A branch may extend an example with robot-specific fields (step ids, frame indices, an
action representation, demonstration provenance); define them in the robot's
pose-record reference rather than here. Extra keys on an example are allowed; the
required keys above must still be present.

## Checking

From the repository or a session workspace:

```bash
python3 skills/experience-memory/scripts/check_memory.py memory/
python3 skills/experience-memory/scripts/check_memory.py memory/ --json
```

The checker walks `TIPS.md`, `INDEX.md` and every `memory/skills/<slug>/`. It confirms
table columns, slug names, learned-skill frontmatter and bullets, `evidence.json`
fields, and that INDEX rows and skill folders agree. An empty `memory/` directory is
valid. Distilled skills without `TIPS.md` are not. Exit status is 1 when anything
breaks the format.

A valid tree is checked in as [examples/ok](../examples/ok). Tests live next to the
script; from the repository root run `python3 skills/run_tests.py`.
