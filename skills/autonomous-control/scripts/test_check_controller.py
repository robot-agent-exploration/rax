#!/usr/bin/env python3
"""Tests for check_controller.py."""
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

import check_controller  # noqa: E402

EXAMPLE = SKILL / "examples" / "ok"
CHECKER = SCRIPTS / "check_controller.py"

CONTROLLER = '''\
def perceive(ctx):
    return {"ok": True, "measured": {}, "why": ""}

def main(ctx):
    seen = perceive(ctx)
    if not seen["ok"]:
        return seen
    return {"ok": True, "measured": {}, "why": "done"}
'''

README = """\
# Demo

Run `controller.py:main(ctx)` from a wrapper outside this directory.

## Perception checkpoints

None
"""

README_TABLE = """\
# Demo

Run `controller.py:main(ctx)` from a wrapper outside this directory.

## Perception checkpoints

| Step | Subagent | Frames | Question | Expected answer | Pass if | On fail |
|---|---|---|---|---|---|---|
| reach | fast | overview.jpg | Is the gripper above the rim? | yes | yes | retreat |
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _messages(issues) -> list[str]:
    return [issue.render() for issue in issues]


class CheckControllerTests(unittest.TestCase):
    def test_example_ok(self):
        issues = check_controller.check_target(EXAMPLE)
        self.assertEqual(issues, [], _messages(issues))

    def test_missing_path(self):
        issues = check_controller.check_target(Path("/no/such/controller-project"))
        self.assertTrue(any("does not exist" in i.message for i in issues))

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues = check_controller.check_target(Path(tmp))
        self.assertTrue(any("no controller.py" in i.message for i in issues))

    def test_missing_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", "def helper(ctx):\n    return {'ok': True}\n")
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertTrue(any("must define main(ctx)" in i.message for i in issues))

    def test_main_without_ctx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "controller.py",
                "def main():\n    return {'ok': True, 'measured': {}, 'why': ''}\n",
            )
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertTrue(any("first argument" in i.message for i in issues))

    def test_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", "def main(ctx)\n    return {}\n")
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertTrue(any("does not compile" in i.message for i in issues))

    def test_opens_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "controller.py",
                "from api.runtime import Context\n"
                "def main(ctx):\n"
                "    with Context() as other:\n"
                "        return {'ok': True, 'measured': {}, 'why': ''}\n",
            )
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertTrue(any("do not open Context()" in i.message for i in issues))
        self.assertTrue(any("do not import Context" in i.message for i in issues))

    def test_return_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", "def main(ctx):\n    return {'ok': True}\n")
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertTrue(any("missing" in i.message and "measured" in i.message for i in issues))

    def test_checkpoint_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "controller.py",
                "def main(ctx):\n"
                "    return {\n"
                "        'ok': True, 'measured': {}, 'why': '',\n"
                "        'checkpoint': {'subagent': 'fast', 'question': 'held?'},\n"
                "    }\n",
            )
            _write(root / "README.md", README_TABLE)
            issues = check_controller.check_target(root)
        self.assertTrue(any("checkpoint is missing" in i.message for i in issues))

    def test_checkpoint_requires_readme_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "controller.py",
                "def main(ctx):\n"
                "    return {\n"
                "        'ok': True, 'measured': {}, 'why': '',\n"
                "        'checkpoint': {\n"
                "            'subagent': 'fast',\n"
                "            'frames': ['a.jpg'],\n"
                "            'question': 'held?',\n"
                "            'answer': 'yes | no',\n"
                "            'pass_if': 'yes',\n"
                "            'on_fail': 'stop',\n"
                "        },\n"
                "    }\n",
            )
            _write(root / "README.md", "# Demo\n\nRun controller.py:main(ctx).\n")
            issues = check_controller.check_target(root)
        self.assertTrue(any("no Perception checkpoints table" in i.message for i in issues))

    def test_missing_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", CONTROLLER)
            issues = check_controller.check_target(root)
        self.assertTrue(any("README.md is missing" in i.message for i in issues))

    def test_readme_without_run_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", CONTROLLER)
            _write(root / "README.md", "# Demo\n\nNo run instructions.\n")
            issues = check_controller.check_target(root)
        self.assertTrue(any("how to run" in i.message for i in issues))

    def test_experiments_inside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", CONTROLLER)
            _write(root / "README.md", README)
            _write(root / "experiments/run_controller.py", "print('no')\n")
            issues = check_controller.check_target(root)
        self.assertTrue(any("outside code/<project>/" in i.message for i in issues))

    def test_workspace_scans_code_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "code" / "mug-reach"
            shutil.copytree(EXAMPLE, project)
            issues = check_controller.check_target(workspace)
        self.assertEqual(issues, [], _messages(issues))

    def test_workspace_flags_missing_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            _write(workspace / "code" / "mug-reach" / "README.md", README)
            issues = check_controller.check_target(workspace)
        self.assertTrue(any("controller.py is missing" in i.message for i in issues))

    def test_cli_ok(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(EXAMPLE)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("OK", result.stdout)

    def test_cli_json_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(CHECKER), tmp, "--json"],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload)
        self.assertIn("message", payload[0])

    def test_none_checkpoints_ok_without_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "controller.py", CONTROLLER)
            _write(root / "README.md", README)
            issues = check_controller.check_target(root)
        self.assertEqual(issues, [], _messages(issues))

    def test_direct_controller_file(self):
        issues = check_controller.check_target(EXAMPLE / "controller.py")
        self.assertEqual(issues, [], _messages(issues))


if __name__ == "__main__":
    unittest.main()
