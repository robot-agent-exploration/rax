#!/usr/bin/env python3
"""Tests for check_memory.py."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_memory  # noqa: E402

EXAMPLE = SKILL / "examples" / "ok"
CHECKER = SCRIPTS / "check_memory.py"

TIPS_TABLE = """\
| Task phase | Preconditions | What worked | Visible effect | Evidence |
|---|---|---|---|---|
| reach | mug on table | move 4 cm above rim | gripper above mug | runtime/frames/a.jpg |
"""

INDEX_ROW = """\
| Skill | Tags | Confirmation | Last confirmed |
|---|---|---|---|
| `skills/reach-mug-rim/SKILL.md` | reach | observed | 2026-10-15 |
"""

SKILL_MD = """\
---
name: learned-reach-mug-rim
description: Reach above a visible mug rim
---

# Reach

- Applies when: mug visible on the table
- Avoid when: mug occluded
- Executed action: move_pose 4 cm above the rim
- Pose recipe: rim point, robot frame, +0.04 m z
- Actions: localize, preview, move
- Expected effect: gripper above the rim
- Recovery: retreat 8 cm along +z
"""

EVIDENCE = {
    "schema_version": 1,
    "skill": "learned-reach-mug-rim",
    "examples": [
        {
            "task": "mug on coaster",
            "episode_or_date": "2026-10-15",
            "confirmation": "observed",
            "frames": ["runtime/frames/a.jpg"],
            "executed_action": {"tool": "move_pose", "arguments": {}},
            "pose_recipe": "rim, robot frame, +0.04 m z",
            "point_reacquisition": "overview rim pixels, depth window",
            "observed_effect": "gripper above rim",
        }
    ],
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _messages(issues) -> list[str]:
    return [issue.render() for issue in issues]


class CheckMemoryTests(unittest.TestCase):
    def test_example_ok_is_clean(self):
        issues = check_memory.check_memory(EXAMPLE)
        self.assertEqual(issues, [], _messages(issues))

    def test_empty_memory_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues = check_memory.check_memory(Path(tmp))
        self.assertEqual(issues, [])

    def test_missing_directory(self):
        issues = check_memory.check_memory(Path("/no/such/memory-dir"))
        self.assertTrue(issues)
        self.assertIn("does not exist", issues[0].message)

    def test_tips_wrong_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "TIPS.md",
                "| Phase | Note |\n|---|---|\n| a | b |\n",
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("columns must be" in i.message for i in issues))

    def test_tips_empty_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "TIPS.md",
                "| Task phase | Preconditions | What worked | Visible effect | Evidence |\n"
                "|---|---|---|---|---|\n"
                "| reach | mug on table | move |  | runtime/frames/a.jpg |\n",
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("Visible effect is empty" in i.message for i in issues))

    def test_index_bad_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(
                root / "INDEX.md",
                "| Skill | Tags | Confirmation | Last confirmed |\n"
                "|---|---|---|---|\n"
                "| `skills/reach-mug-rim/SKILL.md` | reach | maybe | 2026-10-15 |\n",
            )
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("Confirmation must be" in i.message for i in issues))

    def test_index_missing_skill_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            issues = check_memory.check_memory(root)
        self.assertTrue(any("does not exist" in i.message for i in issues))

    def test_skill_missing_from_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(
                root / "INDEX.md",
                "| Skill | Tags | Confirmation | Last confirmed |\n|---|---|---|---|\n",
            )
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("needs a row linking" in i.message for i in issues))

    def test_skill_wrong_frontmatter_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(
                root / "skills/reach-mug-rim/SKILL.md",
                SKILL_MD.replace("learned-reach-mug-rim", "reach-mug-rim"),
            )
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("must be 'learned-reach-mug-rim'" in i.message for i in issues))

    def test_skill_missing_bullet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(
                root / "skills/reach-mug-rim/SKILL.md",
                SKILL_MD.replace("- Recovery: retreat 8 cm along +z\n", ""),
            )
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("Recovery" in i.message for i in issues))

    def test_missing_evidence_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            issues = check_memory.check_memory(root)
        self.assertTrue(any("evidence.json is missing" in i.message for i in issues))

    def test_evidence_missing_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(json.dumps(EVIDENCE))
            payload["examples"][0]["executed_action"] = {"arguments": {}}
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(payload),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any("executed_action" in i.message for i in issues))

    def test_task_confirmed_requires_matching_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(
                root / "INDEX.md",
                INDEX_ROW.replace("observed", "task-confirmed"),
            )
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(
            any("no task-confirmed example" in i.message for i in issues)
        )

    def test_learned_skills_require_tips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(EVIDENCE),
            )
            issues = check_memory.check_memory(root)
        self.assertTrue(any(i.path == "TIPS.md" for i in issues))

    def test_extra_evidence_fields_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(json.dumps(EVIDENCE))
            payload["examples"][0]["step_id"] = 12
            _write(root / "TIPS.md", TIPS_TABLE)
            _write(root / "INDEX.md", INDEX_ROW)
            _write(root / "skills/reach-mug-rim/SKILL.md", SKILL_MD)
            _write(
                root / "skills/reach-mug-rim/evidence.json",
                json.dumps(payload),
            )
            issues = check_memory.check_memory(root)
        self.assertEqual(issues, [], _messages(issues))

    def test_cli_ok_and_json(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(EXAMPLE)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("OK", result.stdout)
        result_json = subprocess.run(
            [sys.executable, str(CHECKER), str(EXAMPLE), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result_json.returncode, 0, result_json.stderr)
        self.assertEqual(json.loads(result_json.stdout), [])

    def test_cli_reports_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "TIPS.md", "no table here\n")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(root)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("markdown table", result.stdout)

    def test_example_survives_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "memory"
            shutil.copytree(EXAMPLE, dest)
            issues = check_memory.check_memory(dest)
        self.assertEqual(issues, [], _messages(issues))


if __name__ == "__main__":
    unittest.main()
