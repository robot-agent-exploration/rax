# Universal agent skills

These are the robot-agnostic, high-level skills that every RAX branch gives its agent,
written once without any robot's names, tools or numbers. Each code branch ships its own
versions under `agent_skills/`, tuned to its robot and setting; this folder is their
common core, ready to copy into a new robot branch. The robot's own `robot-interface`
skill supplies the facts, starting from the [template](templates/robot-interface/SKILL.md);
[`robot-interface/`](robot-interface/SKILL.md) here is only a placeholder, so the
skills' links resolve while you browse.

| Skill | What it gives the agent |
| --- | --- |
| [manual-robot-control](manual-robot-control/SKILL.md) | Solve the task by hand: a completion checklist, small grounded steps, measured versus commanded state, refusals as walls, success confirmed in fresh views. |
| [autonomous-control](autonomous-control/SKILL.md) | Compile what worked into `controller.py:main(ctx)`: invariant motion in the object's frame, step functions returning `{ok, measured, why}`, end-to-end tests from fresh scenes, optional [perception checkpoints](autonomous-control/references/checkpoints.md). |
| [experience-memory](experience-memory/SKILL.md) | Task memory in `memory/`: tips recorded the moment something works, learned skills with evidence ([format](experience-memory/references/format.md)). Check a session tree with [check_memory.py](experience-memory/scripts/check_memory.py). |
| [in-context-action-learning](in-context-action-learning/SKILL.md) | Use image demonstrations for intent and strategy, never as motion data. |
| [transfer-handoff](transfer-handoff/SKILL.md) | A motion-planning handoff for a later session on unseen scenes. |
| [continual-learning](continual-learning/SKILL.md) | A persistent, merged library of verified executable sub-task skills across sessions ([format](continual-learning/references/library-format.md)). |
| [multi-env-exploration](multi-env-exploration/SKILL.md) | Operate parallel environments with one shared episode budget. |
| [multi-agent-exploration](multi-agent-exploration/SKILL.md) | Split exploration among subagents with clear robot ownership ([coordination files](multi-agent-exploration/references/coordination.md)). |
| [vlm-perception](vlm-perception/SKILL.md) | Ask a vision-language model 2-D questions; keep 3-D geometry in code. |
| [camera-inspection](camera-inspection/SKILL.md) | Move a carried camera for a close-up, or look around before sweeping motions. |
| [object-localization](object-localization/SKILL.md) | Pixels to robot-frame points with depth, with RGB and camera geometry, or with RGB and measured motion only ([geometry code](object-localization/references/geometry.md)). |
| [live-stream](live-stream/SKILL.md) | Read the continuous recording before acting after a pause and to review motions. |

## How the harness installs skills

- **Sources** live once per branch under `agent_skills/`, grouped by layer:
  `task/`, `coordination/`, `perception/common/`, `perception/<depth|rgb-only>-<robot>/`,
  `control/<robot>/` and `auto-research/`.
- **Each session's workspace** is built by `services/workspace/`. It copies the layers
  in order (`SKILL_LAYERS` in `services/workspace/recipes.py`); a later layer adds files
  to a skill of the same name or replaces them. It leaves out what the session cannot use
  (`SkillRule`), and renders every Markdown file as a Jinja template against the
  session's facts (`robot.*`).
- **The agent sees one flat directory,** `.agents/skills/<name>/SKILL.md`. Claude Code
  reads the same skills through a `.claude/skills` link. Skills link to each other by
  relative path (`../robot-interface/SKILL.md`), so a universal skill reaches the
  robot's own skills by name, without knowing the robot.

| Layer | Holds | Universal? |
| --- | --- | --- |
| `task/` | `manual-robot-control`, `experience-memory`, `in-context-action-learning`, `continual-learning`; `autonomous-control` on the real-robot branches | yes |
| `coordination/` | `multi-env-exploration`, `multi-agent-exploration` | yes |
| `perception/common/` | `wrist-camera-inspection`, `live-stream` | yes |
| `perception/<mode>-<robot>/` | `object-localization` for one observation mode and robot | method yes, numbers no |
| `control/<robot>/` | `robot-interface` and the robot's motion skills | no |
| `auto-research/` | `gemini`, `transfer-handoff`; `autonomous-control` and its formal-copy variants on the simulation branches | yes |

Skills are left out when the session lacks the capability: `multi-env-exploration`
with one environment, `multi-agent-exploration` without subagents,
`in-context-action-learning` without demonstrations, `transfer-handoff` unless a later
session will continue from `handoff/`, and on the real-robot branches `gemini` without
a model key and `live-stream` without a recorder.

Two skills carry neutral names here: `vlm-perception` is `gemini` on the branches, and
`camera-inspection` is `wrist-camera-inspection`. When you install one, use a single
name throughout: its folder, the links from other skills and any `SkillRule`.

## Universal versus robot-specific

A universal skill is a workflow contract: what to do, in what order, and how to judge
the evidence. Anything with a robot's name or number belongs to that robot's skills:
tools and arguments, frames and units, workspace limits, measured motion accuracy,
gripper behaviour, cameras and calibration, arming and safety rules, and failure
shapes. If a sentence would be false on another robot, it belongs in
`control/<robot>/` or `perception/<mode>-<robot>/`.

The universal skills therefore name tools by role, such as `<observe>` or
`<move_pose>`, and point to `robot-interface` for the facts. The
[tool roles](#tool-roles) table resolves every role on each branch.

## Skills on each branch

Simulation links point at `robodojo-behavior/container`;
`robodojo-behavior/native` has the same skills at the same paths, worded for running
without a container (workspace-relative paths, no session limit on VLM spending).

| Universal skill | Simulation (RoboDojo, BEHAVIOR-1K) | Franka | RB-Y1 | How the branches differ |
| --- | --- | --- | --- | --- |
| manual-robot-control | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/task/manual-robot-control/SKILL.md) | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/task/manual-robot-control/SKILL.md) | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/task/manual-robot-control/SKILL.md) | Sim starts episodes on new layouts and confirms success with `evaluate`. Real robots wait for operator arming and confirm in fresh images from several cameras. RB-Y1 adds active perception (looking around before sweeping motions). |
| autonomous-control | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/auto-research/autonomous-control/SKILL.md), [formal copy](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/auto-research/autonomous-control/SKILL.formal-episode.md) | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/task/autonomous-control/SKILL.md) | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/task/autonomous-control/SKILL.md) | Sim: `register` → `rehearse` → `submit` a frozen controller for held-out layouts, or build one that live copies of the agent supervise. Franka: unattended runs after operator resets. RB-Y1: supervised steps with perception checkpoints, and invariant motion in the object's frame. |
| experience-memory | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/task/experience-memory/SKILL.md), [formal copy](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/auto-research/experience-memory/SKILL.formal-episode.md) | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/task/experience-memory/SKILL.md) | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/task/experience-memory/SKILL.md) | Sim cites frame manifests, episode ids and evidence modes, and formal copies only read carried memory. Real robots cite saved frames and dates and record the conditions under which a tip held. RB-Y1 promotes skills to its library. |
| in-context-action-learning | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/task/in-context-action-learning/SKILL.md) | - | - | Sim only: image demonstrations (a completion sequence or a terminal state). |
| transfer-handoff | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/auto-research/transfer-handoff/SKILL.md) | - | - | Sim only: notes for live copies or a later session on held-out layouts. |
| continual-learning | - | - | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/task/continual-learning/SKILL.md) | Recommended for every real robot: `skill-library/`, merged with `<library_merge>` and published to [skills-lib](https://github.com/robot-agent-exploration/skills-lib). RB-Y1 ships it (`skill_library_merge`). |
| multi-env-exploration | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/coordination/multi-env-exploration/SKILL.md) | - | - | Sim only: parallel environments addressed by `env_id`. |
| multi-agent-exploration | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/coordination/multi-agent-exploration/SKILL.md) | - | - | Sim: robot workers per environment, or turn-taking on one robot. Real robots: one agent commands the robot; subagents analyze (Franka's `AGENTS.md`) or answer perception checkpoints (RB-Y1's autonomous-control). |
| vlm-perception | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/auto-research/gemini/SKILL.md) | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/auto-research/gemini/SKILL.md) | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/auto-research/gemini/SKILL.md) | Named `gemini` on the branches. On the container branch one spending cap covers the whole session, formal batch included; the native branch sets no session limit. RB-Y1 ships a helper module, [`vlm.py`](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/auto-research/gemini/scripts/vlm.py), and prefers the VLM to colour rules. |
| camera-inspection | [sim](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/perception/common/wrist-camera-inspection/SKILL.md) | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/perception/common/wrist-camera-inspection/SKILL.md) | in manual-robot-control | Named `wrist-camera-inspection` on the branches. RB-Y1 has only a head camera: it aims it with `rby1_look_at` and looks around by turning its chest. |
| object-localization | depth: [RoboDojo](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/perception/depth-robodojo/object-localization/SKILL.md), [BEHAVIOR](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/perception/depth-behavior/object-localization/SKILL.md); RGB: [RoboDojo](https://github.com/robot-agent-exploration/rax/blob/robodojo-behavior/container/agent_skills/perception/rgb-only-robodojo/object-localization/SKILL.md) | [depth](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/perception/depth-franka/object-localization/SKILL.md), [RGB](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/perception/rgb-only-franka/object-localization/SKILL.md) | [depth](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/perception/depth-rby1/object-localization/SKILL.md), [RGB](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/perception/rgb-only-rby1/object-localization/SKILL.md) | Sim RGB-only gives no camera geometry, so the agent aligns using measured motion. Real RGB-only keeps intrinsics and camera poses, so the agent can triangulate or intersect a ray with a plane. Tolerances are measured per robot. |
| live-stream | - | [franka](https://github.com/robot-agent-exploration/rax/blob/real/franka/agent_skills/perception/common/live-stream/SKILL.md) | [rby1](https://github.com/robot-agent-exploration/rax/blob/real/rainbow/agent_skills/perception/common/live-stream/SKILL.md) | Real robots only. In sim, motion replies publish their own frame sequences. |

Robot-specific skills stay on their branches: `robot-interface` everywhere; RoboDojo's
`free-space-move`, `pose-math`, `action-preview` and `action-search`; BEHAVIOR's
`free-space-move`, `base-navigation` and `motion-preview`; RB-Y1's `base-navigation`,
`grasping` and `whole-body-control`.

### Simulation and real robots

| | Simulation | Real robot |
| --- | --- | --- |
| Fresh scene | `start_episode` loads the next layout | the operator resets the scene on `request_operator` (`reset`); nothing resets automatically |
| Evaluation | held-out layouts: a frozen controller runs alone (after `register`, `rehearse`, `submit`), or live copies of the agent continue with their controller and carried notes | no formal evaluation: end-to-end runs logged in `memory/RUNS.md`, unattended (Franka) or with perception checkpoints (RB-Y1) |
| Success check | `evaluate`, or native `task_complete` | every `TASK.md` condition in fresh images from more than one camera |
| Parallelism | parallel environments and robot subagents | one robot and one agent commanding it |
| Safety | step and wall-clock budgets | operator arming, a person at the e-stop, backend limits; refusals are walls |
| Seeing change | motion replies publish their frames | a live stream of the recent past |

## Tool roles

| Role | RoboDojo | BEHAVIOR-1K | Franka | RB-Y1 |
| --- | --- | --- | --- | --- |
| `status` (harness) | `status` | `status` | `status` | `status` |
| `<status>` | `robodojo_status` | `behavior_status` | `franka_status` | `rby1_status` |
| `<observe>` | `robodojo_observe` | `behavior_observe` | `franka_observe` | `rby1_observe` |
| `<pixel_to_position>` | `robodojo_pixel_to_position` | `behavior_pixel_to_position` | `franka_pixel_to_position` | `rby1_pixel_to_position` |
| `<move_pose>` | `robodojo_free_space_move` (planned), `robodojo_step_eef` (bounded IK steps) | `behavior_free_space_move` (planned), `behavior_step_eef` | `franka_move_pose` | `rby1_move_eef` |
| `<move_joints>` | `robodojo_step` | `behavior_step` (rows for base, trunk, arms and grippers) | `franka_move_joints` | `rby1_move_joints`, `rby1_move_body` |
| `<gripper>` | gripper fields of `robodojo_step` and `robodojo_step_eef` | gripper entries of `behavior_step` rows | `franka_gripper` | `rby1_gripper` |
| `<base_move>` | - | `behavior_base_move` | - | `rby1_base_move` |
| `<aim_camera>` | - (move an empty arm's wrist camera) | trunk joints through `behavior_step` | - | `rby1_look_at` |
| `<preview>` | `preview_only` plans, `robot_preview_run`, `robodojo_fk_preview` | `preview_only` plans, `behavior_preview_run` | - (`franka_move_joints` checks the whole path before moving) | `rby1_check`, `rby1_fk` |
| `<hold>` | - | - | `franka_hold` | `rby1_hold` |
| `<stream>` | - | - | `franka_stream` | `rby1_stream` |
| `<vlm>` | `gemini_generate` | `gemini_generate` | `gemini_generate` | `gemini_generate` |
| Episodes and evaluation | `start_episode`, `evaluate`, `finish`; `register`, `rehearse`, `submit` for a frozen controller | same | - | - |
| Operator | - | - | `request_operator` | `request_operator` |
| `<library_merge>` | - | - | - | `skill_library_merge` |

Python reaches every tool the same way on every branch: `from api.runtime import
Context`, then `ctx.call(tool, **arguments)`.

## Porting to a new robot

1. **Bring up the backend.** Follow the
   [real-robot adaptation guide](../docs/REAL_ROBOT_ADAPTATION.md) through its
   [bring-up checklist](../docs/REAL_ROBOT_ADAPTATION.md#bring-up-checklist). Fork the
   closest reference branch: `real/franka` for a single arm, `real/rainbow` for a
   mobile or multi-limb robot.
2. **Write the robot's skills** from measured numbers
   ([characterization protocol](../docs/REAL_ROBOT_ADAPTATION.md#characterization-protocol)):
   `robot-interface` from the [template](templates/robot-interface/SKILL.md),
   `object-localization` for each observation profile (fill in its
   [This robot](object-localization/SKILL.md#this-robot) table), and a motion skill for
   each control mode that needs more than the interface says.
3. **Install the universal skills** in the matching layers of `agent_skills/`
   (`task/`, `perception/common/`, `auto-research/`, and `coordination/` only where the
   harness offers parallel environments or robot subagents). Replace each role with the
   robot's tool, or better with the `robot.*` key of `ROBOT_FACTS` in
   `services/workspace/setup.py` (`{{ robot.observe }}`), so one source renders for
   every robot. The keys are `status`, `observe`, `move`, `move_joints`, `gripper`,
   `pixel` and `stream`; `real/rainbow` has the full set.
4. **Gate what the robot lacks.** Add a `SkillRule` for a skill whose capability is
   missing (no recorder, no skill library, no model key) instead of an
   `if robot == ...` in a template.
5. **Check the rendering.** Render a workspace, run the branch's workspace tests, and
   read the skills as the agent will: every link resolves and no other robot's names
   remain.
6. **Run a dry agent session** with a person at the e-stop before real tasks.

See [Keeping robot branches in sync](../docs/REAL_ROBOT_ADAPTATION.md#keeping-robot-branches-in-sync)
for what stays on the robot's branch and what moves between branches.
